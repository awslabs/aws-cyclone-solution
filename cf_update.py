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


import json
import os
import re
import pprint




# This script can be used to convert a cdk synthesised cloudformation template from the front end stack into a CF template that can be deployed directly with CLoudformation API. 
# If you make changes to the front-end-stack then you want these changes to be updated in template.json which is used bt the hyper cli "hyper hosts create-host" command to deploy a
# front-end-architecture without CDK installed for less advanced users. This means the full control plain is deployed with only the AWS CLI and the CDK stack will run in the cloud
# after that and be abstracted from users who only interact with CLI. The template.json only works for importing VPC, not creating. 

# Name your stack place-holder in settings.json and run cdk synth. Afterwards run this script on the generated template.

#USE: cdk synth <stack name> --version-reporting false --path-metadata false --asset-metadata false --no-staging

name = 'place-holder'
account = '123xxxxx9876'
region = 'eu-west-1'
vpc_id = 'vpc-1234xxx1234'
enable_dashboard = 'enable_dashboard_true_or_false'
repo = 'placeholder_repo'
cidr = None
subnet = 'placeholder_subnet'
api_key = 'placeholder_api_key'

import_vpc_True_dash_False = 'cdk.out/place-holder-front-end-us-east-1.template.json'
import_vpc_False_dash_False = ''

current_name = 'place-holder'
current_account = '1234xxxx9876'
current_region ='us-east-1'
current_vpc_id ='vpc-0c74e8ffde4edf579'
current_enable_dashboard = 'enable_dashboard_true_or_false'
current_cidr = None
current_repo ='placeholder_repo'
current_repo_2 = 'aws-cdk/assets'
current_subnet = 'placeholder_subnet'
current_api_key = 'B55M5T1huO-56PWPNGls06uDHErWzPv2SQ'


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config


j = get_config(import_vpc_True_dash_False)

parameters = j['Parameters']
new_parameters = {}
for param in parameters:
    if not 'AssetParameters' in param:
        new_parameters[param] = parameters[param]


j['Parameters'] = new_parameters


resources = j['Resources']

remove = []
for res in resources:
    try:
        del j['Resources'][res]['Metadata']
    except Exception:
        pass
    if 's3deployCustomResource' in res or 's3deployAwsCliLayer' in res or 'CustomS3AutoDeleteObjectsCustomResourceProviderHandler' in res or 'CustomCDKBucketDeployment' in res or 'AutoDeleteObjectsCustomResource' in res or 'imagesPolicy' in res:
        remove.append(res)
    if 'ApiConfigLambda' in res:
        if j['Resources'][res]['Type'] == 'AWS::Lambda::Function':
            j['Resources'][res]['Properties']['Code'] = "13-api-config-lambda/"
    if 'ApiHandlerLambda' in res:
        if j['Resources'][res]['Type'] == 'AWS::Lambda::Function':
            j['Resources'][res]['Properties']['Code'] = "1-api-handler-lambda/"
    if 'layer' in res:
        if j['Resources'][res]['Type'] == 'AWS::Lambda::LayerVersion':
            j['Resources'][res]['Properties']['Content'] = ".lambda_dependencies/"
    if 'ASG' in res:
        if j['Resources'][res]['Type'] == 'AWS::AutoScaling::AutoScalingGroup':
            j['Resources'][res]['Properties']['VPCZoneIdentifier'] = ["placeholder_subnet"]
    if 'dashboard' in res:
        if j['Resources'][res]['Type'] == 'AWS::SSM::Parameter':
            j['Resources'][res]['Properties']['Value'] = "enable_dashboard_true_or_false"
    if 'Taskdef' in res:
        if j['Resources'][res]['Type'] == 'AWS::ECS::TaskDefinition':
            j['Resources'][res]['Properties']['ContainerDefinitions'][0]['Image']['Fn::Join'][1][2] = '/placeholder_repo:orchestrator'      

for res in remove:
    j['Resources'].pop(res)


s = json.dumps(j)

resources = j['Resources']

for res in resources:
    print(str(res))
   # new_res = res[:-8]
   # print(new_res)
    new_res=res
    if current_name in new_res:
        new_res = new_res.replace(current_name, name)
    elif re.sub('[^A-Za-z0-9]+', '', current_name) in new_res:
        new_res = new_res.replace(re.sub('[^A-Za-z0-9]+', '', current_name), re.sub('[^A-Za-z0-9]+', '', name))
    else:
        new_res = re.sub('[^A-Za-z0-9]+', '', name) + new_res
    print(new_res)
    
    s = s.replace(res, new_res)

s = s.replace(current_vpc_id, vpc_id)
s = s.replace(current_region, region)
s = s.replace(current_account, account)
s = s.replace(current_name, name)
s = s.replace(current_repo, repo)
s = s.replace(current_repo_2, repo)
s = s.replace(current_api_key, api_key)
s = s.replace(re.sub('[^A-Za-z0-9]+', '', current_name), re.sub('[^A-Za-z0-9]+', '', name))

s = json.loads(s)

with open("cloudformation/no_vpc/dirty_template_4.json", 'w') as outfile:
                json.dump(s, outfile, indent=4,sort_keys=True)

#pprint.pprint(json.dumps(s))
