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
    aws_batch as batch,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda_event_sources as lambda_event_sources,
    aws_kinesis as kinesis,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_ssm as ssm
    )

from aws_cdk.custom_resources import Provider

import os
import subprocess
import jsii
import boto3
import json
import uuid
import time


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config


cluster_config = get_config("./hyper_batch/configuration/clusters.json")
cluster_config = cluster_config['clusters']
class Clusters(core.Stack):

    def __init__(self, scope: core.Construct, id: str, *, stack_name: str=None, main_region: str=None, is_main_region: str=None, import_vpc: str=None, cidr: str=None, vpc_id: str=None, peer_with_main_region: str=None, deploy_vpc_endpoints: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #create all iam roles here in main region and import them to other stacks to manage destroying stacks without failing dependendencies and creation of stacks not failing due to missing role for import
        if self.region == main_region:

            async_stream_lambda_role = iam.Role(self, "AsyncStreamLambdaRole",
                role_name=stack_name + '-AsyncStreamLambdaRole',
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
            )

            dynamo_stream_lambda_role = iam.Role(self, "DynamoStreamLambdaRole",
                role_name=stack_name + '-DynamoStreamLambdaRole',
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
            )

            # Kinesis batch lambda execution role
            kinesis_batch_lambda_role = iam.Role(self, "KinesisBatchLambdaRole",
                role_name=stack_name + '-KinesisBatchLambdaRole',
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
            )

            iam.Policy(self, 'async-access-policy', roles=[async_stream_lambda_role, dynamo_stream_lambda_role, kinesis_batch_lambda_role],
                statements=[
                    iam.PolicyStatement(resources=["*"], actions=[
                        "kinesis:GetRecords",
                        "kinesis:GetShardIterator",
                        "kinesis:ListShards",
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams"
                    ]),
                    iam.PolicyStatement(resources=['*'], actions=[
                        'dynamodb:ListStreams',
                        'dynamodb:DescribeStream',
                        'dynamodb:GetRecords',
                        'dynamodb:GetShardIterator',
                        "dynamodb:Query",
                        "dynamodb:UpdateItem"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:s3:::{stack_name}-images-{self.region}',f'arn:aws:s3:::{stack_name}-images-{self.region}/*'], actions=[
                        "s3:*",
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:kms:{self.region}:{self.account}:key/*'], actions=[
                        "kms:Decrypt"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:logs:{self.region}:{self.account}:*'], actions=[
                        "logs:CreateLogGroup",
				        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ])
                ],
                policy_name=self.stack_name + '-Kinesis'
                )

            instanceRole = iam.Role(self, str(self.stack_name + '-instanceRole'),
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore')],
            )
            iam.Policy(self, 'instance-role-policy', roles=[instanceRole],
                statements=[
                    iam.PolicyStatement(resources=["*"], actions=[
                        "ec2:DescribeTags",
                        "ecs:CreateCluster",
                        "ecs:DeregisterContainerInstance",
                        "ecs:DiscoverPollEndpoint",
                        "ecs:Poll",
                        "ecs:RegisterContainerInstance",
                        "ecs:StartTelemetrySession",
                        "ecs:UpdateContainerInstancesState",
                        "ecs:Submit*",
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ]),
                ],
                policy_name=self.stack_name + '-instance-role-policy'
            )

            cfn_instance_profile = iam.CfnInstanceProfile(self, "InstanceProfile",
                roles=[instanceRole.role_name],
                instance_profile_name=stack_name + '-InstanceProfile'
            )

        else:
            dynamo_lambda_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-DynamoStreamLambdaRole'
            dynamo_stream_lambda_role = iam.Role.from_role_arn(self, "DynamoStreamLambdaRole", role_arn=dynamo_lambda_role_arn, add_grants_to_resources=False, mutable=False)
            kinesis_batch_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-KinesisBatchLambdaRole'
            kinesis_batch_lambda_role = iam.Role.from_role_arn(self, "KinesisBatchLambdaRole", role_arn=kinesis_batch_role_arn, add_grants_to_resources=False, mutable=False)

        ##################################
        # vpc for clusters and vpc peering connections
  
        #create vpc or import existing
        if import_vpc == 'False':
            vpc = ec2.Vpc(self, id='hyper_batch_vpc', cidr=cidr)
        else:
            vpc = ec2.Vpc.from_lookup(self, id='hyper_batch_vpc', vpc_id=vpc_id)   
        
        core.Tags.of(vpc).add(key=stack_name, value=self.region)

        #vpc endpoints
        if deploy_vpc_endpoints == 'DATA_OPTIMISED':
            vpc.add_gateway_endpoint(str(stack_name + 'dynamo-endpoint'), service=ec2.GatewayVpcEndpointAwsService.DYNAMODB)
            vpc.add_gateway_endpoint(str(stack_name + 's3-endpoint'), service=ec2.GatewayVpcEndpointAwsService.S3)
            ecr_api_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecr-api-endpoint'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecr.api', port=443))
            ecr_dkr_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecr-dkr-endpoint'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecr.dkr', port=443))
            kinesis_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'kinesis-endpoint'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.kinesis-streams', port=443))
        if deploy_vpc_endpoints == 'FOR_PRIVATE_VPC':
            vpc.add_gateway_endpoint(str(stack_name + 'dynamo-endpoint'), service=ec2.GatewayVpcEndpointAwsService.DYNAMODB)
            vpc.add_gateway_endpoint(str(stack_name + 's3-endpoint'), service=ec2.GatewayVpcEndpointAwsService.S3)
            ecr_api_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecr-api-endpoint'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecr.api', port=443))
            ecr_dkr_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecr-dkr-endpoint'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecr.dkr', port=443))
            ecs_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecs'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecs', port=443))
            ecs_agent_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecs_agent'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecs-agent', port=443))
            ecs_tel_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'ecs-telemetry'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.ecs-telemetry', port=443))
            kinesis_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'kinesis-endpoint'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.kinesis-streams', port=443))
            sf_states_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'sf-states'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.states', port=443))
            sf_sync_states_endpoint = ec2.InterfaceVpcEndpoint(self, str(stack_name + 'sf-sync-states'), vpc=vpc, private_dns_enabled=True, service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{self.region}.sync-states', port=443))

        lambda_layer = self.create_dependencies_layer(stack_name, "layers-clusters")

        if is_main_region == 'True':

            ssm.StringParameter(self, str(stack_name + '-vpc-id-param'),
                allowed_pattern=".*",
                description="main region vpc id",
                parameter_name=str(stack_name + '-main-vpc-id'),
                string_value=vpc.vpc_id,
                tier=ssm.ParameterTier.ADVANCED
            )
            ssm.StringParameter(self, str(stack_name + '-vpc-cidr-param'),
                allowed_pattern=".*",
                description="main region vpc cidr",
                parameter_name=str(stack_name + '-main-vpc-cidr'),
                string_value=vpc.vpc_cidr_block,
                tier=ssm.ParameterTier.ADVANCED
            )

        #peer with main region vpc
        if is_main_region == 'False' and peer_with_main_region == 'True':
            ssm_client = boto3.client('ssm', region_name=main_region)
            main_vpc_id = 'null'
            main_vpc_cidr = 'null'
            try:
                main_vpc_id = ssm_client.get_parameter(
                    Name=str(stack_name + '-main-vpc-id'),
                )
                main_vpc_id = main_vpc_id['Parameter']['Value']

                main_vpc_cidr = ssm_client.get_parameter(
                    Name=str(stack_name + '-main-vpc-cidr'),
                )
                main_vpc_cidr = main_vpc_cidr['Parameter']['Value']
            except Exception:
                pass
            
            route_table_arns = []
            peering = ec2.CfnVPCPeeringConnection(self, id=str(stack_name + 'peering'), vpc_id=vpc.vpc_id, peer_vpc_id=main_vpc_id, peer_region=main_region)
            for subnet in vpc.private_subnets:
                route = ec2.CfnRoute(self, subnet.availability_zone + '-route', route_table_id=subnet.route_table.route_table_id, destination_cidr_block=main_vpc_cidr, vpc_peering_connection_id=peering.ref)
                route_table_arns.append(f'arn:aws:ec2:{main_region}:{self.account}:route-table/{subnet.route_table.route_table_id}')

           #event rule to trigger lambda that modifies route table in main region to include new hub region after request for peering
            vpc_peering_lambda_role = iam.Role(self, "PeeringLambdaRole",
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
            )

            iam.Policy(self, 'vpc-peering-policy', roles=[vpc_peering_lambda_role],
                statements=[
                    iam.PolicyStatement(resources=["*"], actions=[
                        "ec2:DescribeRouteTables",
				        "ec2:DescribeSubnets",
				        "ec2:DescribeVpcs"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:ec2:{main_region}:{self.account}:route-table/*'], actions=[
                        "ec2:CreateRoute",
                        "ec2:ReplaceRoute",
                        "ec2:DeleteRoute",
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:ec2:{main_region}:{self.account}:vpc-peering-connection/*'], actions=[
                        "ec2:ModifyVpcPeeringConnectionOptions"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:kms:{self.region}:{self.account}:key/*'], actions=[
                        "kms:Decrypt"
                    ]),
                    iam.PolicyStatement(resources=[f'arn:aws:logs:{self.region}:{self.account}:*'], actions=[
                        "logs:CreateLogGroup",
				        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ])
                ],
                policy_name=self.stack_name + '-peering-access'
                )

            vpc_peering_lambda = _lambda.Function(self, str(stack_name + 'vpc-peering-lambda'),
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="vpc-peering-lambda.lambda_handler",
                code=_lambda.Code.asset('12-vpc-peering-lambda'),
                role=vpc_peering_lambda_role,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.ACTIVE,
            )
            vpc_peering_lambda.add_environment("MAIN_REGION", main_region)
            vpc_peering_lambda.add_environment("MAIN_VPC_ID", main_vpc_id)
            vpc_peering_lambda.add_environment("PEERING_ID", peering.ref)
            vpc_peering_lambda.add_environment("HUB_CIDR", vpc.vpc_cidr_block)

            provider = Provider(self, str(stack_name + 'provider'),
                    on_event_handler=vpc_peering_lambda
                    )
            
            core.CustomResource(self, str(stack_name + 'CustomRoutesMainRegion'),
                service_token=provider.service_token,
                removal_policy=core.RemovalPolicy.DESTROY,
                resource_type="Custom::MainRegionVPCPeeringRoutes"
            )

        #Put the worker agent in s3 bucket where it is retrived by workers at start-up using the start.sh script triggered as part of initial command passed to worker
        worker_script_bucket = s3.Bucket(self, str(stack_name +'-worker'),
            bucket_name=str(stack_name + '-worker-'+ self.region),
            public_read_access=False,
            removal_policy=core.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption= s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            server_access_logs_prefix='access-logs',
            enforce_ssl=True
            )

        s3deploy.BucketDeployment(self, str(stack_name +'-s3deploy'),

            sources=[s3deploy.Source.asset("0-worker-agent")],
            destination_bucket=worker_script_bucket
        )

        stream_arns = []
        job_queue_arns =[]
        # Batch - ComputeEnvironment - Batch Job Queue
        for cluster in cluster_config:

            # creates the kinesis stream to recive requests for resource or reduction in resource and the Lambda to process and submit jobs to aws batch
            # Kinesis batch lambda execution role

            # Kinesis stream for downstream processing
            kinesis_stream = kinesis.Stream(self, str(stack_name + cluster['clusterName'] + '-stream'), stream_name=cluster['clusterName'], stream_mode=kinesis.StreamMode('ON_DEMAND'))

            stream_arns.append(kinesis_stream.stream_arn)

            # Kinesis batch lambda
            kinesis_batch_lambda = _lambda.Function(self, str(stack_name + cluster['clusterName'] + '-lambda'),
                runtime=_lambda.Runtime.PYTHON_3_8,
                handler="kinesis-batch-lambda.lambda_handler",
                code=_lambda.Code.asset('3-kinesis-batch-lambda'),
                role=kinesis_batch_lambda_role,
                timeout=core.Duration.seconds(180),
                layers=[lambda_layer],
                tracing=_lambda.Tracing.ACTIVE,
            )

            kinesis_batch_lambda.add_environment("REGION", self.region)
            kinesis_batch_lambda.add_environment("MAIN_REGION", main_region)
            kinesis_batch_lambda.add_environment("STACK_NAME", stack_name)
            kinesis_batch_lambda.add_environment("WORKER_SCRIPT_S3KEY", str(worker_script_bucket.bucket_name + '/batch_processor.py'))

            # Update Lambda Permissions To Use Stream
            kinesis_stream.grant_read(kinesis_batch_lambda)

            # Create New Kinesis Event Source
            kinesis_event_source = lambda_event_sources.KinesisEventSource(
                stream=kinesis_stream,
                starting_position=_lambda.StartingPosition.LATEST,
                batch_size=1000,
                parallelization_factor=10,
                max_batching_window=core.Duration.minutes(1),
                retry_attempts=0
            )

            # Attach New Event Source To Lambda
            kinesis_batch_lambda.add_event_source(kinesis_event_source)

            batchServiceRole = iam.Role(self, str(stack_name + cluster['clusterName'] + '-' + self.region),
                assumed_by=iam.ServicePrincipal("batch.amazonaws.com"),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSBatchServiceRole")],
                )
            
            for policy in cluster['iam_policies']:
                batchServiceRole.add_managed_policy(policy=iam.ManagedPolicy.from_managed_policy_name(self, id=cluster['clusterName'] + policy, managed_policy_name=policy))


            instance_list = cluster['instance_list']
            instance_types = []
            for type_string in instance_list:
                instace_type = ec2.InstanceType(type_string)
                instance_types.append(instace_type)

            envs = []
            if cluster['max_vCPUs'] == 0:
                max_vCPUs = 0
            else:
                max_vCPUs = round(0.5 + cluster['max_vCPUs'] / 3)
            
            image_object = None
            if not cluster['main_region_image_name'] == None or cluster['main_region_image_name'] == '':
                ec2_local = boto3.client('ec2', region_name=self.region)
                images = ec2_local.describe_images(Filters=[{'Name': 'name', 'Values': [cluster['main_region_image_name']]}])
            
                if len(images['Images']) > 0:
                    for image in images['Images']:
                        if image['Name'] == cluster['main_region_image_name']:
                            print('Found {} in {}'.format(cluster['main_region_image_name'], self.region))
                            ami_id = image['ImageId']
                            image_object = ec2.MachineImage.generic_linux({self.region : ami_id})

                else:
                    print('Could not find AMI {} in {}, copying it from main region'.format(cluster['main_region_image_name'], self.region))
                    ec2_main = boto3.client('ec2', region_name=main_region)
                    main_images = ec2_main.describe_images(Filters=[{'Name': 'name', 'Values': [cluster['main_region_image_name']]}])
            
                    if len(main_images['Images']) > 0:
                        for image in main_images['Images']:
                            if image['Name'] == cluster['main_region_image_name']:
                                ami_id = image['ImageId']
                    
                    else:
                        print('DID NOT FIND {} in {}'.format(cluster['main_region_image_name'], main_region))
                        raise ValueError

                    raw_ami_id = ec2_local.copy_image(
                        Name=cluster['main_region_image_name'],
                        SourceImageId=ami_id,
                        SourceRegion=main_region
                    )
                    ami_id = raw_ami_id['ImageId']
                    while True:
                        time.sleep(30)
                        copy_images = ec2_local.describe_images(ImageIds=[ami_id])
                        if copy_images['Images'][0]['State'] == 'pending':
                            print('COPY PENDING')
                            continue
                        elif copy_images['Images'][0]['State'] == 'available' and copy_images['Images'][0]['Name'] == cluster['main_region_image_name']:
                            print('Copy successful')
                            break
                        else:
                            print('COPY FAILED')
                            print(json.dumps(copy_images))
                            raise ValueError

            
                    if len(main_images['Images']) > 0:
                        for image in main_images['Images']:
                            if image['Name'] == cluster['main_region_image_name']:
                                ami_id = image['ImageId']
                    ami_id = raw_ami_id['ImageId']
                    image_object = ec2.MachineImage.generic_linux({self.region : ami_id})
                    print('AMI copied and available to cyclone')



            lt_raw = ec2.CfnLaunchTemplate(self, stack_name + '-' + cluster['clusterName'] + '-' + 'lt',
                launch_template_name=stack_name + '-' + cluster['clusterName'] + '-' + 'lt',
                launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(instance_type="t3.small")
                )
            lt = batch.LaunchTemplateSpecification(launch_template_name=lt_raw.launch_template_name)

            for i in range(1, 4, 1):
                CE_name = batch.ComputeEnvironment(self, id=stack_name + '-' + cluster['clusterName'] + '-' + str(i),
                    compute_resources={
                        "type": batch.ComputeResourceType(cluster['type']),
                        "allocation_strategy": batch.AllocationStrategy(cluster['allocation_strategy']),
                        "instance_types": instance_types,
                        "launch_template": lt,
                        "image": image_object,
                        "bid_percentage": cluster['bid_percentage'], # Bids for resources at 75% of the on-demand price
                        "vpc": vpc,
                        "maxv_cpus": int(cluster['max_vCPUs'] / 3),
                        "instance_role": f'arn:aws:iam::{self.account}:instance-profile/{stack_name}-InstanceProfile'
                    },
                    service_role=batchServiceRole,
                )

                ENV_name =  batch.JobQueueComputeEnvironment(
                    # Defines a collection of compute resources to handle assigned batch jobs
                    compute_environment=CE_name,
                    # Order determines the allocation order for jobs (i.e. Lower means higher preferance for job assignment)
                    order=i
                )
                envs.append(ENV_name)

            jobQueue = batch.JobQueue(self, str(stack_name + cluster['clusterName'] + '-queue'), compute_environments=envs, priority=1)

            job_queue_arns.append(jobQueue.job_queue_arn)


            #map the kinesis stream lambda processor to this AWS Batch job queue
            kinesis_batch_lambda.add_environment("BATCH_JOB_QUEUE", jobQueue.job_queue_name)

        #give the dynamo_stream_lambda in main region access to the cluster streams in this region for resource requests
        if len(cluster_config) > 0:
            iam.Policy(self, 'cluster-stream-access', roles=[dynamo_stream_lambda_role],
                statements=[
                    iam.PolicyStatement(resources=stream_arns, actions=[
                        "kinesis:DescribeStreamSummary",
                        "kinesis:GetRecords",
                        "kinesis:GetShardIterator",
                        "kinesis:ListShards",
                        "kinesis:SubscribeToShard",
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams",
                        "kinesis:PutRecord"
                    ]),
                ],
                policy_name=self.stack_name + '-cluster-stream-access'
                )

            iam.Policy(self, 'batch-access-policy', roles=[kinesis_batch_lambda_role],
                    statements=[
                        iam.PolicyStatement(resources=job_queue_arns, actions=[
                            "batch:SubmitJob",
                            "batch:TagResource"
                        ]),
                        iam.PolicyStatement(resources=[f'arn:aws:batch:{self.region}:{self.account}:job-definition/*'], actions=[
                            "batch:SubmitJob",
                            "batch:TagResource"
                        ])
                        ,
                        iam.PolicyStatement(resources=[f'arn:aws:ssm:{self.region}:{self.account}:parameter/*'], actions=[
                            "ssm:GetParameter",
                        ])
                    ],
                    policy_name=self.stack_name + '-batch-access'
                    )

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