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
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    )
from constructs import Construct
import json
import boto3
import cdk_ecr_deployment as ecrdeploy


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

images = get_config("./hyper_batch/configuration/images.json")
images = images['images']

def repo_exist(stack_name, region):
    ecr_client = boto3.client('ecr', region_name=region)
    try:
        response = ecr_client.describe_repositories(
            repositoryNames=[stack_name]
        )
        print('Found existing repo')
        return True
    except Exception:
        print('No existing repo')
        return False

class Images(core.Stack):

  def __init__(self, scope: Construct, id: str, *, main_region: str=None, stack_name: str=None,  **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        if repo_exist(stack_name, self.region):
            repo = ecr.Repository.from_repository_name(self, str(self.stack_name + '-repo'), repository_name=str(stack_name))
        else:
            repo = ecr.Repository(self, str(self.stack_name + '-repo'),image_scan_on_push=True, repository_name=str(stack_name), removal_policy=core.RemovalPolicy.RETAIN)

        
        for image in images:

          
            asset = ecr_assets.DockerImageAsset(self, image['imageName'],
                                                            directory= image['directory'],
                                                            build_args=image.get('build_arguments', None)
                                                )
            
            ecrdeploy.ECRDeployment(self, str(self.stack_name + image['imageName']),
              src=ecrdeploy.DockerImageName(asset.image_uri),
              dest=ecrdeploy.DockerImageName(f"{repo.repository_uri}:{image['imageName']}")
          )


