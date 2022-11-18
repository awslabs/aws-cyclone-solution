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
    aws_logs as logs,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_s3_deployment as s3deploy,
    aws_appsync as appsync,
    aws_backup as backup,
    aws_autoscaling as autoscaling
    )
from constructs import Construct
import os
import subprocess
import boto3
import secrets
import json

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

settings = get_config("./hyper_batch/configuration/settings.json")

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
                            print('It is not owned by this front-end stack, must be the queue stack')
                            return True, 'null'
            except Exception as e:
                print('There was an issue checking what stack ownes the deployment and/or existing api key')
                print(e)
                pass
            api_key = ssm_client.get_parameter(
                Name=str(stack_name + '_api_key'))
            api_key = api_key['Parameter']['Value']
            print('It is owned by this front-end stack so keeping it with same api key')
            api_key = api_key
            return False, api_key
    print('Did not find existing front-end api, deploying in this stack with new api key')
    api_key = secrets.token_urlsafe(25)
    return False, api_key


class HyperFrontEnd(core.Stack):

  def __init__(self, scope: Construct, id: str, *, account: str=None, stack_name: str=None, enable_dashboard: str=None, import_vpc: str=None, vpc_id: str=None, cidr: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # DynamoDB Tables
        hyper_clusters_table = dynamodb.Table(self, stack_name + '-clusters-table',
                                        partition_key=dynamodb.Attribute(
                                        name='name', type=dynamodb.AttributeType.STRING
                                        ),
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        table_name=stack_name + '_clusters_table',
                                        encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                        removal_policy=core.RemovalPolicy.DESTROY
        )
        
        hyper_queues_table = dynamodb.Table(self, stack_name + '-queues-table',
                                        partition_key=dynamodb.Attribute(
                                        name='name', type=dynamodb.AttributeType.STRING
                                        ),
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        table_name=stack_name + '_queues_table',
                                        encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                        removal_policy=core.RemovalPolicy.DESTROY
        )

        hyper_regions_table = dynamodb.Table(self, stack_name + '-regions-table',
                                        partition_key=dynamodb.Attribute(
                                        name='name', type=dynamodb.AttributeType.STRING
                                        ),
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        table_name=stack_name + '_regions_table',
                                        encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                        removal_policy=core.RemovalPolicy.DESTROY
        )

        hyper_jobDefinitions_table = dynamodb.Table(self, stack_name + '-jobDefinitions-table',
                                        partition_key=dynamodb.Attribute(
                                        name='name', type=dynamodb.AttributeType.STRING
                                        ),
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        table_name=stack_name + '_jobDefinitions_table',
                                        encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                        removal_policy=core.RemovalPolicy.DESTROY
        )

        hyper_images_table = dynamodb.Table(self, stack_name + '-images-table',
                                        partition_key=dynamodb.Attribute(
                                        name='name', type=dynamodb.AttributeType.STRING
                                        ),
                                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                                        table_name=stack_name + '_images_table',
                                        encryption=dynamodb.TableEncryption.AWS_MANAGED,
                                        removal_policy=core.RemovalPolicy.DESTROY
        )

        #Backup tables
        vault = backup.BackupVault(self, str(stack_name +'-backup-vault'), backup_vault_name=str(stack_name +'-backup-vault'), removal_policy=core.RemovalPolicy.DESTROY)
        plan = backup.BackupPlan.daily35_day_retention(self, str(stack_name +'-backup-tables'), backup_vault=vault)

        plan.add_selection("Selection",
            resources=[
                backup.BackupResource.from_dynamo_db_table(hyper_images_table),
                backup.BackupResource.from_dynamo_db_table(hyper_jobDefinitions_table),
                backup.BackupResource.from_dynamo_db_table(hyper_clusters_table),
                backup.BackupResource.from_dynamo_db_table(hyper_queues_table),
                backup.BackupResource.from_dynamo_db_table(hyper_regions_table)
            ]
        )

        deployed, api_key_value = check_api_exists(self.region, stack_name)

        if import_vpc == 'False':
            vpc = ec2.Vpc(self, id='hyper_batch_vpc', cidr=cidr)
        else:
            vpc = ec2.Vpc.from_lookup(self, id='hyper_batch_vpc', vpc_id=vpc_id)   #this fails due to credentials so cannot import vpc
        
        core.Tags.of(vpc).add(key=stack_name, value=self.region)


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

            private_api = settings.get('private_api', 'False')

            if private_api == 'True':

                self.secure_private_api_01_sec_grp = ec2.SecurityGroup(
                    self,
                    "secureApi01SecurityGroup",
                    vpc=vpc,
                    allow_all_outbound=True,
                    description="Miztiik Automation: Secure our private API using security groups"
                )

                # Allow 443 inbound on our Security Group
                self.secure_private_api_01_sec_grp.add_ingress_rule(
                    ec2.Peer.ipv4(vpc.vpc_cidr_block),
                    ec2.Port.tcp(443)
                )

                secure_private_api_01_endpoint = ec2.InterfaceVpcEndpoint(
                    self,
                    "secureApi01Endpoint",
                    vpc=vpc,
                    service=ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
                    private_dns_enabled=True,
                    subnets=ec2.SubnetSelection(
                        subnet_type=ec2.SubnetType.ISOLATED
                    )
                )

                # Create a API Gateway Resource Policy to attach to API GW
                # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-restapi.html#cfn-apigateway-restapi-policy
                secure_private_api_01_res_policy = iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            principals=[iam.AnyPrincipal()],
                            actions=["execute-api:Invoke"],
                            # resources=[f"{api_01.arn_for_execute_api(method="GET",path="greeter", stage="miztiik")}"],
                            resources=[core.Fn.join("", ["execute-api:/", "*"])],
                            effect=_iam.Effect.DENY,
                            conditions={
                                "StringNotEquals":
                                {
                                    "aws:sourceVpc": f"{secure_private_api_01_endpoint.vpc_endpoint_id}"
                                }
                            },
                            sid="DenyAllNonVPCAccessToApi"
                        ),
                        iam.PolicyStatement(
                            principals=[_iam.AnyPrincipal()],
                            actions=["execute-api:Invoke"],
                            resources=[core.Fn.join("", ["execute-api:/", "*"])],
                            effect=_iam.Effect.ALLOW,
                            sid="AllowVPCAccessToApi"
                        )
                    ]
                )


                job_api = apigateway.LambdaRestApi(self, str(stack_name +'-job-api'),
                    handler=api_config_lambda,
                    endpoint_types=[
                        apigateway.EndpointType.PRIVATE
                    ],
                    policy=secure_private_api_01_res_policy,
                    api_key_source_type=apigateway.ApiKeySourceType.HEADER,
                    deploy_options={
                    "logging_level": apigateway.MethodLoggingLevel.ERROR,
                    "data_trace_enabled": False,
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
            
            else:

                job_api = apigateway.LambdaRestApi(self, str(stack_name +'-job-api'),
                    handler=api_config_lambda,
                    api_key_source_type=apigateway.ApiKeySourceType.HEADER,
                    deploy_options={
                    "logging_level": apigateway.MethodLoggingLevel.ERROR,
                    "data_trace_enabled": False,
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
                server_access_logs_prefix='access-logs',
                enforce_ssl=True
                )

            s3deploy.BucketDeployment(self, str(stack_name +'-s3deploy'),

                sources=[s3deploy.Source.asset("hyper_batch/configuration/images/")],
                destination_bucket=image_bucket,
                destination_key_prefix='images/'
            )


        cluster = ecs.Cluster(self, str(stack_name +'-ECSCluster'), cluster_name= stack_name+'-orch-cluster', vpc=vpc, container_insights=True)
        cluster.apply_removal_policy(core.RemovalPolicy.DESTROY)

        auto_scaling_group = autoscaling.AutoScalingGroup(self, str(stack_name +'-ASG'),
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.2xlarge"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            min_capacity=0,
            max_capacity=1
        )

        capacity_provider = ecs.AsgCapacityProvider(self, stack_name+"_CapPro", capacity_provider_name=str(stack_name + '-CapPro'),
            auto_scaling_group=auto_scaling_group
        )
        cluster.add_asg_capacity_provider(capacity_provider)
        
        taskRole = iam.Role(self, str(stack_name +'-ECSRole'),
                assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")]
                )

        taskDef = ecs.Ec2TaskDefinition(self, str(stack_name +'-Taskdef'), family=str(stack_name +'-Taskdef'), execution_role=taskRole, task_role=taskRole)

        asset = ecr_assets.DockerImageAsset(self, str(stack_name +'-ECSImage'),
                                                            directory= '.'
                                                )

        container = ecs.ContainerImage.from_docker_image_asset(asset)

        taskDef.add_container(str(stack_name +'-ECSAddContainer'), memory_limit_mib=20500, privileged=True, image=container, environment={'ACCOUNT':account, 'STACK_NAME':stack_name, 'REGION':self.region, 'DEPLOYED':'True'}, logging=ecs.AwsLogDriver(stream_prefix=str(stack_name +'-orchestrator'), log_retention=logs.RetentionDays.TWO_MONTHS)
        ).add_mount_points(ecs.MountPoint(container_path='/var/run/docker.sock',source_volume='var',read_only=False), ecs.MountPoint(container_path='/usr/bin/docker',source_volume='bin',read_only=False))
        var_host = ecs.Host(source_path='/var/run/docker.sock')
        bin_host = ecs.Host(source_path='/usr/bin/docker')
        taskDef.add_volume(name='var', host=var_host)
        taskDef.add_volume(name='bin', host=bin_host)

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

