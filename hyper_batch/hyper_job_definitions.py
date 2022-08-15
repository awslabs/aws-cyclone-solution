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
    aws_batch as batch,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_ssm as ssm,
    aws_ec2 as ec2
    )

import json


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config
def bool_convert(string):
    if 'False' or 'false' in string:
        return False
    elif 'True' or 'true' in string:
        return True
    else:
        return string

job_definitions_config = get_config("./hyper_batch/configuration/job_definitions.json")
job_definitions = job_definitions_config['jobDefinitions']

class JobDefinitions(core.Stack):

  def __init__(self, scope: core.Construct, id: str, *, is_main_region: str=None, stack_name: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if is_main_region == 'True':
            async_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-AsyncStreamLambdaRole'
            async_stream_lambda_role = iam.Role.from_role_arn(self, "AsyncStreamLambdaRole", role_arn=async_role_arn, add_grants_to_resources=False, mutable=False)
            dynamo_lambda_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-DynamoStreamLambdaRole'
            dynamo_stream_lambda_role = iam.Role.from_role_arn(self, "DynamoStreamLambdaRole", role_arn=dynamo_lambda_role_arn, add_grants_to_resources=False, mutable=False)

        sqs_arns = []

        for job_definition in job_definitions:

            ecsInstanceRole = iam.Role(self, job_definition['jobDefinitionName']+'-InstanceRoleJobDef',
                role_name=self.stack_name + '-' + job_definition['jobDefinitionName'],
                assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role")]       
                )

            for policy in job_definition['iam_policies']:
                ecsInstanceRole.add_managed_policy(policy=iam.ManagedPolicy.from_managed_policy_name(self, id=job_definition['jobDefinitionName'] + policy, managed_policy_name=policy))
            

            iam.Policy(self, job_definition['jobDefinitionName'] + 'worker-access', roles=[ecsInstanceRole], statements=[
                iam.PolicyStatement(resources=[f'arn:aws:dynamodb:{self.region}:{self.account}:table/{stack_name}-core*'], actions=['dynamodb:UpdateItem', 'dynamodb:GetItem', 'dynamodb:PutItem']),
                iam.PolicyStatement(resources=[f'arn:aws:kinesis:{self.region}:{self.account}:stream/{stack_name}_log_stream'], actions=[
                    "kinesis:DescribeStreamSummary",
                    "kinesis:SubscribeToShard",
                    "kinesis:PutRecord"
                    ]),
                iam.PolicyStatement(
                    actions=[
                        "kms:Decrypt",
                        "kms:GenerateDataKey"
                    ],
                    resources=[f"arn:aws:kms:{self.region}:{self.account}:key/*"]),
                iam.PolicyStatement(
                    actions=[
                        "states:SendTaskSuccess",
                        "states:SendTaskFailure",
                        "states:SendTaskHeartbeat"
                    ],
                    resources=['*']),
                iam.PolicyStatement(
                    actions=[
                        "states:StartExecution"
                    ],
                    resources=[f'arn:aws:states:{self.region}:{self.account}:stateMachine:{stack_name}*']),
                iam.PolicyStatement(
                    actions=["s3:*"],
                    resources=[f'arn:aws:s3:::{stack_name}-worker-{self.region}*'])
                ],
                policy_name=self.stack_name + '-worker-access'
            )



            if job_definition['use_cyclone_image'] == "True":
                image_uri = '{}.dkr.ecr.{}.amazonaws.com/{}:{}'.format(self.account, self.region, stack_name, job_definition['cyclone_image_name'])
            else:
                image_uri = job_definition['image_uri']

            container = ecs.ContainerImage.from_registry(image_uri)

            # specify mount_points in config file with [] or for example: [{"container_path": "c-path", "read_only": False, "source_volume": "s-volume"}]
            try:
                if not job_definition['mount_points'] == None:
                    mount_point_list = job_definition['mount_points']
                    mount_points = []
                    for point in mount_point_list:
                        mount_point = ecs.MountPoint(
                            container_path=point['container_path'],
                            read_only=bool_convert(point['read_only']),
                            source_volume=point['source_volume']
                        )
                        mount_points.append(mount_point)
                else:
                    mount_points = None
            except Exception as e:
                print(e)
                print(f'ERROR: mount_point list could not be interpreted --  {mount_point_list}')

            log_config = None
            try:
                if 'log_driver' in str(job_definition):
                    if not job_definition['log_driver'] == None or not job_definition['log_driver'] == '':
                        log_driver = batch.LogDriver(job_definition['log_driver'])
                else:
                    log_driver = None
                if not log_driver == None:
                    options = job_definition['log_options'] or None
                    log_config = batch.LogConfiguration(log_driver=log_driver, options=options)
                else:
                    log_config = None
            except Exception as e:
                print(e)
                print(f'ERROR: log configs could not be interpreted' )

            try:
                if 'linux_parameters' in job_definitions:
                    print(job_definition['linux_parameters'])
                    linux_parameters = ecs.LinuxParameters(self, str(job_definition['jobDefinitionName'] + '-LinuxParams'),
                        init_process_enabled=bool_convert(job_definition['linux_parameters']['init_process_enabled']),
                        shared_memory_size=job_definition['linux_parameters']['shared_memory_size']
                        )
                else:
                    linux_parameters = None
            except Exception as e:
                print(e)
                print(f'ERROR: linux_parameters could not be interpreted' )


            try:
                if not job_definition['host_volumes'] == None:
                    host_volumes_list = job_definition['host_volumes']
                    host_volumes = []
                    for host_volume in host_volumes_list:
                        volume = ecs.Volume(name=host_volume['name'], host=ecs.Host(source_path=host_volume['source_path']))
                        host_volumes.append(volume)
                else:
                    host_volumes = None
            except Exception as e:
                print(e)
                print(f'ERROR:host_volume list could not be interpreted --  {str(host_volumes)}')

            try:
                if type(job_definition['ulimits']) == list:
                    ulimits_list = job_definition['ulimits']
                    ulimits = []
                    for limit in ulimits_list:
                        ulimits.append(ecs.Ulimit(
                            hard_limit=limit['hard_limit'],
                            name=ecs.UlimitName(limit['UlimitName']),
                            soft_limit=limit['soft_limit']
                        ))
                else:
                    ulimits = None
            except Exception as e:
                print(e)
                ulim = json.dumps(job_definition['ulimits'])
                print(f'ERROR: ulimits could not be interpreted, use null to turn off --  {ulim}')

            if job_definition['environment'] == None or job_definition['environment'] == '':
                    job_definition['environment'] = {}
            job_definition['environment']['CYCLONE_REGION'] = self.region
            if job_definition['enable_qlog'] == "False" or job_definition['enable_qlog'] == False:
                job_definition['environment']['ENABLE_QLOG'] = "False"

            container_def = batch.JobDefinitionContainer(
                image=container,
                memory_limit_mib=job_definition['memory_limit_mib'] or 1024,
                vcpus=job_definition['vcpus'] or 1,
                job_role=ecsInstanceRole,
                linux_params=linux_parameters or None,
                mount_points=mount_points or None,
                volumes=host_volumes or None,
                log_configuration=log_config,
                ulimits=ulimits or None,
                gpu_count=job_definition['gpu_count'] or None,
                environment=job_definition['environment'] or None,
                privileged=bool_convert(job_definition['privileged']) or None,
                user=job_definition['user'] or None
            )
        
            try:
                timeout_minutes = core.Duration.minutes(job_definition['timeout_minutes'])
            except Exception:
                timeout_minutes = None
                pass


            batch.JobDefinition(self, id=job_definition['jobDefinitionName'], job_definition_name=job_definition['jobDefinitionName'],
                                            container=container_def,
                                            timeout=timeout_minutes
                                        )


            ssm.StringParameter(self, str(job_definition['jobDefinitionName'] + '-param'),
                allowed_pattern=".*",
                description="job definition attribute",
                parameter_name=job_definition['jobDefinitionName'],
                string_value=str(job_definition['jobs_to_workers_ratio']),
                tier=ssm.ParameterTier.ADVANCED
            )
            
            if is_main_region == 'True':
                    
                # SQS queue for downstream processing
                queue = sqs.Queue(self, str(job_definition['jobDefinitionName'] + '-q'), queue_name=job_definition['jobDefinitionName'])
                core.Tags.of(queue).add(key='jobs_to_workers_ratio', value=str(job_definition['jobs_to_workers_ratio']))
                sqs_arns.append(queue.queue_arn)
        
        if is_main_region == 'True':
            if len(job_definitions) > 0:
                iam.Policy(self, 'sqs-access', roles=[async_stream_lambda_role, dynamo_stream_lambda_role], statements=[iam.PolicyStatement(resources=sqs_arns, actions=['sqs:SendMessage', "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueUrl"])], policy_name=self.stack_name + '-jobDef-access')


