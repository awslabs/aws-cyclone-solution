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
    aws_iam as iam,
    aws_elasticsearch as es,
    aws_ssm as ssm,
    aws_opensearchservice as opensearch
    )

import os
import subprocess
import jsonpickle
import boto3
import json

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

class Dashboard(core.Stack):

  def __init__(self, scope: core.Construct, id: str, *, stack_name: str=None, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        async_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-AsyncStreamLambdaRole'
        async_stream_lambda_role = iam.Role.from_role_arn(self, "AsyncStreamLambdaRole", role_arn=async_role_arn, add_grants_to_resources=False, mutable=False)
        dynamo_lambda_role_arn = f'arn:aws:iam::{self.account}:role/{stack_name}-DynamoStreamLambdaRole'
        dynamo_stream_lambda_role = iam.Role.from_role_arn(self, "DynamoStreamLambdaRole", role_arn=dynamo_lambda_role_arn, add_grants_to_resources=False, mutable=False)


        domain = opensearch.Domain(self, str(stack_name + '-es-domain'),
                           version=opensearch.EngineVersion.OPENSEARCH_1_2,
                           use_unsigned_basic_auth=True,
                           domain_name=str(stack_name + '-es-domain'),
                           removal_policy=core.RemovalPolicy.DESTROY,
                           )
        domain.add_access_policies(iam.PolicyStatement(
                                  actions=["es:*ESHttpPost", "es:ESHttpPut*", "es:ESHttpGet"],
                                  effect=iam.Effect.ALLOW,
                                  principals=[iam.ArnPrincipal(async_stream_lambda_role.role_arn), iam.ArnPrincipal(dynamo_stream_lambda_role.role_arn)],
                                  resources=[domain.domain_arn, f'{domain.domain_arn}/*'],
                              ))


        domain.grant_path_read_write('workers', iam.AccountPrincipal(self.account))
        domain.grant_path_read_write('jobs', iam.AccountPrincipal(self.account))
        domain.grant_path_read_write('job_history', iam.AccountPrincipal(self.account))
        domain.grant_path_read_write('job_logs', iam.AccountPrincipal(self.account))


        domain.grant_index_read_write('jobs', iam.ServicePrincipal("lambda.amazon.com"))
        domain.grant_index_read_write('job_history', iam.ServicePrincipal("lambda.amazon.com"))
        domain.grant_index_read_write('job_logs', iam.ServicePrincipal("lambda.amazon.com"))
        domain.grant_index_read_write('workers', iam.ServicePrincipal("lambda.amazon.com"))

        
        param_domain = ssm.StringParameter(self, id=str(stack_name + "-es-endpoint"), string_value=domain.domain_endpoint, parameter_name=str(stack_name + "-es-endpoint"))

        iam.Policy(self, 'dashboard-access', roles=[async_stream_lambda_role, dynamo_stream_lambda_role],
            statements=[
                iam.PolicyStatement(resources=[domain.domain_arn, domain.domain_arn + '/*'],
                    actions=[
                            "es:ESHttpDelete",
                            "es:ESHttpPost",
                            "es:ESHttpPut",
                            "es:ESHttpPatch"
                        ]),
                iam.PolicyStatement(resources=[param_domain.parameter_arn],
                    actions=[
                        "ssm:DescribeParameters",
                        "ssm:GetParameters",
                        "ssm:GetParameter",
                        "ssm:GetParameterHistory"
                    ]),
            ],
            policy_name=self.stack_name + '-es-access')
