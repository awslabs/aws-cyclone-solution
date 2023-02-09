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

import aws_cdk as core
from aws_cdk import (
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigateway as apigateway,
    aws_ssm as ssm,
    aws_logs as logs,
    aws_s3 as s3
    )
from constructs import Construct
import os
import subprocess
import boto3
import json
import secrets

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

queue_config = get_config("./hyper_batch/configuration/queues.json")
queue_config = queue_config['queues']

all_regions = get_config("./hyper_batch/configuration/regions.json")
all_regions = all_regions['regions']

clusters = get_config("./hyper_batch/configuration/clusters.json")
clusters = clusters['clusters']

def check_api_exists(main_region, stack_name):
    ssm_client = boto3.client('ssm', region_name=main_region)
    name_check = stack_name + '-job-api'
    api_gw = ec2 = boto3.client('apigateway', region_name=main_region)
    response = api_gw.get_rest_apis()

    items = response['items']
    for api in items:
        if name_check == api['name']:
            print('Found existing front-end api')
            try:
                for k,v in api['tags'].items():
                    if k == 'aws:cloudformation:stack-name' and str(stack_name + '-queues-') in v:
                            api_key = ssm_client.get_parameter(
                                Name=str(stack_name + '_api_key'))
                            api_key = api_key['Parameter']['Value']
                            print('It is owned by this queue stack so keeping it with same api key')
                            return False, api_key
            except Exception as e:
                print('There was an issue checking what stack ownes the deployment and/or existing api key')
                print(e)
                pass
            print('It is not owned by this queue stack, must be the front-end stack')
            return True, 'null'
    print('Did not find existing front-end api, deploying in this stack with new api key')
    api_key = secrets.token_urlsafe(25)
    return False, api_key

def default_weights(regions):
        weights = {}
        for region in regions:
                if region in ['us-east-1', "us-east-2", "us-west-1", "eu-west-1", "ap-southeast-1"]:
                    weights[region] = 5
                else:
                    weights[region] = 1
        m = min(weights.values())
        for k,v in weights.items():
            weights[k] = int(v/m)
        return weights

def calculate_weights(cluster_name, region_weight_distributions):

        ec2 = boto3.client('ec2')

        for cluster in clusters:

            print("Processing cluster", cluster["clusterName"], "looking for", cluster_name)
            if cluster["clusterName"] != cluster_name:
                continue

            instance_types = cluster["instance_list"]
            max_vcpus = cluster["max_vCPUs"]


            regions = [k for k,v in region_weight_distributions.items()]
            print("Regions: ", regions)

            # for optimal we need to use static weights, because the instance types are generated at runtime based on the batch job definition
            # It should be fine to use 1 for most regions except for the largest ones, where we can probably use 5.
            if instance_types == ['optimal']:
                return default_weights(regions)

            weights = {}
            try:
                print(instance_types)
                print(max_vcpus)
                print(regions)
                target = int(max_vcpus)
                while True:
                    print('TARGET vCPUs: ', target)
                    try:
                        response = ec2.get_spot_placement_scores(
                            InstanceTypes=instance_types,
                            TargetCapacity=int(target),
                            TargetCapacityUnitType='vcpu',
                            SingleAvailabilityZone=False,
                            RegionNames=regions
                            )
                        break
                    except BaseException as err:
                        if 'TargetCapacityLimitExceeded' in str(err):
                            target = 0.5 * target
                            pass
                        else:
                            print(f"Unexpected exception {err}, {type(err)} while getting spot placement scores, using default weights")
                            break


                contents = response['SpotPlacementScores']

                for item in contents:
                    print('Item:', item)
                    weights[item['Region']] = item['Score'] ** 2
            except BaseException as err:
                try:
                    print(f"Unexpected exception {err}")
                except Exception:
                    pass
                return default_weights(regions)
            try:
                m = min(weights.values())
                for k,v in weights.items():
                    weights[k] = int(v/m)
                return weights
            except BaseException as err:
                print(f"Unexpected exception {err}, {type(err)} while getting spot placement scores, using default weights")
                return default_weights(regions)

class Queues(core.Stack):

    def __init__(self, scope: Construct, id: str, *, main_region: str=None, stack_name: str=None, enable_dashboard: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        async_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-AsyncStreamLambdaRole'
        async_stream_lambda_role = iam.Role.from_role_arn(self, "AsyncStreamLambdaRole", role_arn=async_role_arn, add_grants_to_resources=False, mutable=False)
        dynamo_lambda_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-DynamoStreamLambdaRole'
        dynamo_stream_lambda_role = iam.Role.from_role_arn(self, "DynamoStreamLambdaRole", role_arn=dynamo_lambda_role_arn, add_grants_to_resources=False, mutable=False)
        kinesis_batch_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-KinesisBatchLambdaRole'
        kinesis_batch_lambda_role = iam.Role.from_role_arn(self, "KinesisBatchLambdaRole", role_arn=kinesis_batch_role_arn, add_grants_to_resources=False, mutable=False)

        lambda_layer = self.create_dependencies_layer(stack_name, "layers-queues")
        deployed, api_key_value = check_api_exists(main_region, stack_name)
        if not deployed:
            ############ Job handling API via API Gateway
            # API handler lambda execution role
            api_handler_lambda_role = iam.Role(self, str(stack_name +'ApiHandlerLambdaRole'),
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")       
            )

            iam.Policy(self, 'api-access', roles=[api_handler_lambda_role],
                statements=[
                    iam.PolicyStatement(resources=[f'arn:aws:dynamodb:{self.region}:{self.account}:table/*'], actions=[
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:ConditionCheckItem",
                        "dynamodb:PutItem",
                        "dynamodb:DescribeTable",
                        "dynamodb:DeleteItem",
                        "dynamodb:GetItem",
                        "dynamodb:Scan",
                        "dynamodb:Query",
                        "dynamodb:UpdateItem",
                        "dynamodb:DescribeLimits"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:s3:::{stack_name}-images-{self.region}',f'arn:aws:s3:::{stack_name}-images-{self.region}/*'], actions=[
                        "s3:*",
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:kms:{self.region}:{self.account}:key/*'], actions=[
                        "kms:Decrypt"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:ecs:{self.region}:{self.account}:task-definition/{stack_name}*'], actions=[
                        "ecs:RunTask"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:iam::{self.account}:role/{stack_name}*'], actions=[
                        "iam:PassRole"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:logs:{self.region}:{self.account}:*'], actions=[
                        "logs:CreateLogGroup",
				        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ])
                ],
                policy_name=self.stack_name + '-api-access'
                )

            lambda_layer = self.create_dependencies_layer(stack_name, "layers-front")

            # API handler lambda
            api_handler_lambda = _lambda.Function(self, str(stack_name +'ApiHandlerLambda'),
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="api-handler-lambda.lambda_handler",
                code=_lambda.Code.from_asset('1-api-handler-lambda'),
                role=api_handler_lambda_role,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.DISABLED
            )

            api_config_lambda = _lambda.Function(self, str(stack_name +'ApiConfigLambda'),
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="api-config-lambda.lambda_handler",
                code=_lambda.Code.from_asset('13-api-config-lambda'),
                role=api_handler_lambda_role,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.DISABLED
            )
            api_config_lambda.add_environment("STACK_NAME", stack_name)

            job_api = apigateway.LambdaRestApi(self, str(stack_name +'-job-api'),
                handler=api_config_lambda,
                api_key_source_type=apigateway.ApiKeySourceType.HEADER,
                deploy_options={
                "logging_level": apigateway.MethodLoggingLevel.ERROR,
                "data_trace_enabled": True,
                "access_log_destination": apigateway.LogGroupLogDestination(logs.LogGroup(self, str(stack_name +'-logs-api'), retention=logs.RetentionDays('TWO_MONTHS'))),
                "access_log_format": apigateway.AccessLogFormat.json_with_standard_fields(
                        caller=True,
                        http_method=True,
                        ip=True,
                        protocol=True,
                        request_time=True,
                        resource_path=True,
                        response_length=True,
                        status=True,
                        user=True
                    )}
            )
            
            job_api_jobs = job_api.root.add_resource("jobs")
            job_integration = apigateway.LambdaIntegration(api_handler_lambda)
            job_method = job_api_jobs.add_method("POST", job_integration, api_key_required=True)

            job_api_config = job_api.root.add_resource("config")
            config_integration = apigateway.LambdaIntegration(api_config_lambda)
            config_method = job_api_config.add_method("POST", config_integration, api_key_required=True)

            job_usage_plan = job_api.add_usage_plan("job_usage_plan", throttle=apigateway.ThrottleSettings(rate_limit=10000, burst_limit=5000))
            key = job_api.add_api_key('job_api_key', api_key_name=str(stack_name +'-api-key'), value=api_key_value)
            job_usage_plan.add_api_key(key)

            job_usage_plan.add_api_stage(stage=job_api.deployment_stage, throttle=[
                apigateway.ThrottlingPerMethod(
                    method=job_method,
                    throttle=apigateway.ThrottleSettings(
                        rate_limit=10000,
                        burst_limit=5000
                    )
                ),
                apigateway.ThrottlingPerMethod(
                    method=config_method,
                    throttle=apigateway.ThrottleSettings(
                        rate_limit=1,
                        burst_limit=2
                    )
                )
                ]
            )
            config_url = job_api.url + 'config'
            job_url = job_api.url + 'jobs'
            core.CfnOutput(self, "API_URL", value=config_url)
            ssm.StringParameter(self, str(stack_name + '-api-url-ssm'), string_value=config_url, parameter_name=str(stack_name + '_api_url'))

            core.CfnOutput(self, "API_KEY", value=api_key_value)
            ssm.StringParameter(self, id=str(stack_name + "-api-key-ssm"), string_value=api_key_value, parameter_name=str(stack_name + '_api_key'))

            core.CfnOutput(self, "JOB_URL", value=job_url)
            ssm.StringParameter(self, id=str(stack_name + "_job_url"), string_value=job_url, parameter_name=str(stack_name + '_job_url'))

            ssm.StringParameter(self, id=str(stack_name + "_enable_dashboard"), string_value=enable_dashboard, parameter_name=str(stack_name + '_enable_dashboard'))

            image_bucket = s3.Bucket(self, str(stack_name +'-images'),
                bucket_name=str(stack_name + '-images-'+ self.region),
                public_read_access=False,
                removal_policy=core.RemovalPolicy.DESTROY,
                auto_delete_objects=True,
                encryption= s3.BucketEncryption.S3_MANAGED,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
             #   server_access_logs_prefix='access-logs',
                enforce_ssl=True
                )

        table_arns =[]
        table_stream_arns = []
        for queue in queue_config:

            queue_table = dynamodb.Table(self, id=queue['queue_name'],
                                            partition_key=dynamodb.Attribute(
                                            name='id', type=dynamodb.AttributeType.STRING
                                            ),
                                            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
                                            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                            table_name=queue['queue_name'],
                                            encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                            removal_policy=core.RemovalPolicy.DESTROY
            )

            table_arns.append(queue_table.table_arn)
            table_stream_arns.append(queue_table.table_stream_arn)

            queue_table.add_global_secondary_index(
                index_name='index_jobDefinition',
                partition_key=dynamodb.Attribute(
                    name='jobDefinition', type=dynamodb.AttributeType.STRING
                )
            )

            queue_table.add_global_secondary_index(
                index_name='index_jobName',
                partition_key=dynamodb.Attribute(
                    name='jobName', type=dynamodb.AttributeType.STRING
                )
            )
            
            # Dynamo stream lambda
            dynamo_stream_lambda = _lambda.Function(self, str('lambda-' + queue['queue_name']),
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="dynamo-stream-lambda.lambda_handler",
                code=_lambda.Code.from_asset('2-dynamo-stream-lambda'),
                role=dynamo_stream_lambda_role,
                memory_size=1024,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.DISABLED
            )

            dynamo_stream_lambda.add_environment("CLUSTER_MAPPING", queue['computeEnvironment'])
            dynamo_stream_lambda.add_environment("REGION", self.region)
            dynamo_stream_lambda.add_environment("MAIN_REGION", main_region)

            if queue['optimise_lowest_spot_cost_region'] == 'True':
                try:
                    weights_list = calculate_weights(queue['computeEnvironment'], queue['region_distribution_weights'])
                    weights_list = dict(sorted(weights_list.items()))
                    print(weights_list)
                    queue['region_distribution_weights'] = weights_list
                except Exception:
                    region_weight_distributions = queue['region_distribution_weights']
                    regions_here = [k for k,v in region_weight_distributions.items()]
                    queue['region_distribution_weights'] = default_weights(regions_here)

            dynamo_stream_lambda.add_environment("REGION_DISTRIBUTION_WEIGHTS", str(queue['region_distribution_weights']))

           # queue_table.grant_stream_read(dynamo_stream_lambda)

            dynamo_stream_lambda.add_event_source(
                lambda_event_sources.DynamoEventSource(table=queue_table, 
                                                        starting_position=_lambda.StartingPosition.LATEST,
                                                        batch_size=100,
                                                        parallelization_factor=10,
                                                        max_batching_window=core.Duration.minutes(1),
                                                        retry_attempts=3,
                                                        )
            )

            #Dynamo queue to log stream
            # Dynamo stream lambda
            dynamo_to_logs_lambda = _lambda.Function(self, str('lambda-logs-' + queue['queue_name']),
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="dynamo-to-logs-lambda.lambda_handler",
                code=_lambda.Code.from_asset('10-dynamo-to-logs-lambda'),
                role=dynamo_stream_lambda_role,
                memory_size=1024,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.DISABLED
            )

            dynamo_to_logs_lambda.add_environment("STACK_NAME", stack_name)
            dynamo_to_logs_lambda.add_environment("REGION", self.region)
            dynamo_to_logs_lambda.add_environment("MAIN_REGION", main_region)

         #   queue_table.grant_stream_read(dynamo_to_logs_lambda)

            dynamo_to_logs_lambda.add_event_source(
                lambda_event_sources.DynamoEventSource(table=queue_table, 
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
                

                # Dynamo-to-es lambda
                dynamo_to_es_lambda = _lambda.Function(self, str('lambda_dynamo_es-' + queue['queue_name']),
                    runtime=_lambda.Runtime.PYTHON_3_8,
                    handler="dynamo-to-es.lambda_handler",
                    code=_lambda.Code.from_asset('6-dynamo-to-elasticsearch'),
                    role=dynamo_stream_lambda_role,
                    memory_size=1024,
                    timeout=core.Duration.seconds(180),
                    layers=[lambda_layer],
                    tracing=_lambda.Tracing.DISABLED
                )

                dynamo_to_es_lambda.add_environment("REGION", self.region)
                dynamo_to_es_lambda.add_environment("MAIN_REGION", main_region)
                dynamo_to_es_lambda.add_environment("STACK_NAME", stack_name)


              #  queue_table.grant_stream_read(dynamo_to_es_lambda)

                dynamo_to_es_lambda.add_event_source(
                    lambda_event_sources.DynamoEventSource(table=queue_table, 
                                                            starting_position=_lambda.StartingPosition.LATEST,
                                                            batch_size=100,
                                                            parallelization_factor=10,
                                                            max_batching_window=core.Duration.minutes(1),
                                                            retry_attempts=3,
                                                            )
                )
        
        if len(queue_config) > 0:
            iam.Policy(self, 'queue-access', roles=[async_stream_lambda_role, kinesis_batch_lambda_role, dynamo_stream_lambda_role],
                statements=[
                    iam.PolicyStatement(resources=table_arns, actions=['dynamodb:UpdateItem', 'dynamodb:GetItem']),
                    iam.PolicyStatement(resources=['*'], actions=['xray:PutTraceSegments', 'xray:PutTelemetryRecords'])
                ],
                policy_name=self.stack_name + '-queue-access')


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