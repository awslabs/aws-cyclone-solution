#  Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda_event_sources as lambda_event_sources,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_ssm as ssm,
    aws_events as events,
    aws_kinesis as kinesis,
    aws_events_targets as targets
    )

import os
import subprocess

class HyperBatchCore(core.Stack):

  def __init__(self, scope: core.Construct, id: str, *, stack_name: str=None, main_region: str=None, is_main_region: str=None, import_vpc: str=None, cidr: str=None, vpc_id: str=None, peer_with_main_region: str=None, enable_dashboard: str=None,  **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        async_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-AsyncStreamLambdaRole'
        async_stream_lambda_role = iam.Role.from_role_arn(self, "AsyncStreamLambdaRole", role_arn=async_role_arn, add_grants_to_resources=False, mutable=False)
        
        dynamo_lambda_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-DynamoStreamLambdaRole'
        dynamo_stream_lambda_role = iam.Role.from_role_arn(self, "DynamoStreamLambdaRole", role_arn=dynamo_lambda_role_arn, add_grants_to_resources=False, mutable=False)
 

        ##################################
        # DynamoDB Table for communication between SF and workers in region or on-premise
        Async_table = dynamodb.Table(self, id='GlobalAsyncTable',
                                        partition_key=dynamodb.Attribute(
                                        name='uuid', type=dynamodb.AttributeType.STRING
                                        ),
                                        stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        table_name=self.stack_name + '_table',
                                        encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                        removal_policy=core.RemovalPolicy.DESTROY
        )

        ssm.StringParameter(self, str(stack_name + '-t-param'),
            allowed_pattern=".*",
            description="job definition attribute",
            parameter_name=str(stack_name + '-table'),
            string_value=Async_table.table_name,
            tier=ssm.ParameterTier.ADVANCED
        )

        ##################################
        #resources to move data updates from a-sync table to job queue table

        lambda_layer = self.create_dependencies_layer(stack_name, "layers-core")

        # Kinesis stream all log ingestion, filtering and storing in s3
        kinesis_log_stream = kinesis.Stream(self, stack_name + 'log-stream', stream_name=stack_name + '_log_stream', stream_mode=kinesis.StreamMode('ON_DEMAND'))

        iam.Policy(self, 'async-access-policy', roles=[async_stream_lambda_role, dynamo_stream_lambda_role],
            statements=[
                iam.PolicyStatement(resources=[Async_table.table_arn], actions=['dynamodb:UpdateItem', 'dynamodb:GetItem']),
                iam.PolicyStatement(resources=[kinesis_log_stream.stream_arn], actions=[
                    "kinesis:DescribeStreamSummary",
                    "kinesis:SubscribeToShard",
                    "kinesis:PutRecord"
                ]),
            ],
            policy_name=self.stack_name + '-async-logKinesis-access'
            )
        
        

        # Kinesis batch lambda
        log_stream_lambda = _lambda.Function(self, stack_name + 'log-stream-lambda',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="log-stream-lambda.lambda_handler",
            code=_lambda.Code.asset('9-log-stream-lambda'),
            role=async_stream_lambda_role,
            timeout=core.Duration.seconds(720),
            layers=[lambda_layer],
            tracing=_lambda.Tracing.DISABLED,
        )

        log_stream_lambda.add_environment("STACK_NAME", stack_name)
        log_stream_lambda.add_environment("MAIN_REGION", main_region)

        # Create New Kinesis Event Source
        kinesis_event_source = lambda_event_sources.KinesisEventSource(
            stream=kinesis_log_stream,
            starting_position=_lambda.StartingPosition.LATEST,
            batch_size=5000,
            parallelization_factor=1,
            max_batching_window=core.Duration.minutes(1),
            retry_attempts=3
        )
        # Attach New Event Source To Lambda
        log_stream_lambda.add_event_source(kinesis_event_source)


        # async stream lambda
        async_stream_lambda = _lambda.Function(self, "AsyncStreamLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="async-stream-lambda.lambda_handler",
            code=_lambda.Code.asset('5-async-stream-lambda'),
            role=async_stream_lambda_role,
            memory_size=1024,
            timeout=core.Duration.seconds(180),
            layers=[lambda_layer],
            tracing=_lambda.Tracing.DISABLED
        )

        async_stream_lambda.add_environment("REGION", self.region)
        async_stream_lambda.add_environment("MAIN_REGION", main_region)

        async_stream_lambda.add_event_source(
            lambda_event_sources.DynamoEventSource(table=Async_table, 
                                                    starting_position=_lambda.StartingPosition.LATEST,
                                                    batch_size=100,
                                                    parallelization_factor=10,
                                                    max_batching_window=core.Duration.minutes(1),
                                                    retry_attempts=3,
                                                    )
        )

        #async to logs
        async_to_logs_lambda = _lambda.Function(self, str('lambda-async-logs-' + stack_name),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="async-to-logs-lambda.lambda_handler",
            code=_lambda.Code.asset('11-async-to-logs-lambda'),
            role=async_stream_lambda_role,
            memory_size=1024,
            timeout=core.Duration.seconds(180),
            layers=[lambda_layer],
            tracing=_lambda.Tracing.DISABLED
        )

        async_to_logs_lambda.add_environment("STACK_NAME", stack_name)
        async_to_logs_lambda.add_environment("REGION", self.region)
        async_to_logs_lambda.add_environment("MAIN_REGION", main_region)

        async_to_logs_lambda.add_event_source(
            lambda_event_sources.DynamoEventSource(table=Async_table, 
                                                    starting_position=_lambda.StartingPosition.LATEST,
                                                    batch_size=100,
                                                    parallelization_factor=10,
                                                    max_batching_window=core.Duration.minutes(1),
                                                    retry_attempts=3,
                                                    )
        )

        ##################################
        #lambda to get stream updates and send to es if dashboard is enabled
        if enable_dashboard == "True":

            # Async-to-es lambda
            async_to_es_lambda = _lambda.Function(self, "AsyncToEsLambda",
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="async-to-es.lambda_handler",
                code=_lambda.Code.asset('7-async-to-elasticsearch'),
                role=async_stream_lambda_role,
                memory_size=1024,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.DISABLED
            )

            async_to_es_lambda.add_environment("REGION", self.region)
            async_to_es_lambda.add_environment("MAIN_REGION", main_region)
            async_to_es_lambda.add_environment("STACK_NAME", stack_name)

            async_to_es_lambda.add_event_source(
                lambda_event_sources.DynamoEventSource(table=Async_table, 
                                                        starting_position=_lambda.StartingPosition.LATEST,
                                                        batch_size=100,
                                                        parallelization_factor=10,
                                                        max_batching_window=core.Duration.minutes(1),
                                                        retry_attempts=3,
                                                        )
            )

        ##################################
        # STEP FUNCTIONS state machine to get jobs of sqs and pass to async table to be picked up by batch processor

        # getjob, write to dynamodb and delete from queue
        get_start_delete_lambda = _lambda.Function(self, "GetStartDeleteLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="get-start-delete-lambda.lambda_handler",
            code=_lambda.Code.asset('4-get-start-delete-lambda'),
            timeout=core.Duration.seconds(180),
            role=async_stream_lambda_role,
            layers=[lambda_layer],
            tracing=_lambda.Tracing.DISABLED,
        );

        get_start_delete_lambda.add_environment("MAIN_REGION", main_region)

        #workflow  
        GetStartDelete = tasks.LambdaInvoke(self, 'Get Start Delete Job',
            lambda_function= get_start_delete_lambda,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat= core.Duration.seconds(60),
            payload= sfn.TaskInput.from_object({
                'TaskToken': sfn.JsonPath.task_token,
                'Input': sfn.JsonPath.string_at('$'),
            }),
            result_path= '$.lastJob',
        );

        finish = sfn.Succeed(self, 'Finish',
            comment= 'Shutdown container and finishing'
            )

        CleanUpDynamo = tasks.DynamoDeleteItem(self, 'CleanUpDynamo',
            key= { 'uuid': tasks.DynamoAttributeValue.from_string(sfn.JsonPath.string_at('$.uuid'))},
            table= Async_table,
            input_path='$',
            result_path= '$.CleanDynamoResponse',
        );

        UpdateFail = tasks.DynamoUpdateItem(self, 'Update With Fail',
            key= { 'uuid': tasks.DynamoAttributeValue.from_string(sfn.JsonPath.string_at('$.uuid'))},
            table= Async_table,
            input_path='$',
            update_expression="set #attr1 = :p",
            expression_attribute_names={'#attr1': 'Status'},
            expression_attribute_values={':p': tasks.DynamoAttributeValue.from_string('Failed')},
            result_path= '$.UpdateFailOutput'
        );

        LookAtResult = sfn.Choice(self, 'LookAtResult').when(sfn.Condition.is_present('$.lastJob.Error'),  UpdateFail).when(sfn.Condition.string_equals('$.lastJob.LeaveRunning', 'False'), CleanUpDynamo).when(sfn.Condition.string_equals('$.lastJob.Status', 'Successful'), GetStartDelete).otherwise(UpdateFail)

        ContinueOrFinish = sfn.Choice(self, 'ContinueOrFinish').when(sfn.Condition.string_equals('$.lastJob.Error', 'States.Timeout'), CleanUpDynamo).otherwise(GetStartDelete)

        definition = GetStartDelete.add_catch(LookAtResult, result_path='$.lastJob').next(LookAtResult)
        UpdateFail.next(ContinueOrFinish)
        CleanUpDynamo.next(finish)

        machine = sfn.StateMachine(self, str(stack_name + '-SfM'),
            definition=definition,
            timeout=core.Duration.minutes(10080),
            state_machine_name=str(stack_name + '-SfM'),
            tracing_enabled=False
        );

        ssm.StringParameter(self, str(stack_name + '-sf-param'),
            allowed_pattern=".*",
            description="sf arn attribute",
            parameter_name=str(stack_name + '-SF-ARN'),
            string_value=machine.state_machine_arn,
            tier=ssm.ParameterTier.ADVANCED
        )

        failed_worker_lambda = _lambda.Function(self, str(stack_name + 'failed-worker'),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="failed-worker-lambda.lambda_handler",
            code=_lambda.Code.asset('8-failed-worker-lambda'),
            role=async_stream_lambda_role,
            timeout=core.Duration.seconds(180),
            layers=[lambda_layer],
            tracing=_lambda.Tracing.DISABLED,
        )
        failed_worker_lambda.add_environment("MAIN_REGION", main_region)

        rule = events.Rule(self, "rule",
            event_pattern=events.EventPattern(
                source=["aws.batch"],
                detail_type=["Batch Job State Change"],
                detail={"status": ["FAILED"]}
            )
        )

        rule.add_target(targets.LambdaFunction(failed_worker_lambda))


  def create_dependencies_layer(self, project_name, layer_name: str) -> _lambda.LayerVersion:
        requirements_file = "lambda-requirements.txt"
        output_dir = ".lambda_dependencies"
        if os.path.exists(output_dir):
            print('Lambda dependencies found in local directory')
            os.environ['SKIP_PIP'] = 'True'
        else:
            print('Lambda dependencies not found in local directory, downloading instead')
            os.environ['SKIP_PIP'] = 'False'
        if os.environ.get("SKIP_PIP") == 'False':
            subprocess.check_call(
                f"pip install -r {requirements_file} -t {output_dir}/python".split()
            )
        return _lambda.LayerVersion(
            self,
            project_name + layer_name,
            code=_lambda.Code.from_asset(output_dir)
        )



