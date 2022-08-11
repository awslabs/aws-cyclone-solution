#!/usr/bin/env python3
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

from aws_cdk import core
from hyper_batch.hyper_front_end import HyperFrontEnd
from hyper_batch.hyper_batch_core import HyperBatchCore
from hyper_batch.hyper_clusters import Clusters
from hyper_batch.hyper_queue import Queues
from hyper_batch.hyper_job_definitions import JobDefinitions
from hyper_batch.hyper_image_baker import Images
from hyper_batch.hyper_dashboard import Dashboard
import json
import jsii
import os

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

#get configurations for stack from hyper_batch/configurations/settings.json and pull in region config from
settings = get_config("./hyper_batch/configuration/settings.json")
stack_name = settings['stack_settings']['stack_name']
account = settings['stack_settings']['account']
enable_dashboard = settings['stack_settings']['enable_dashboard']
#get region configurations from hyper_batch/configurations/regions.json
all_regions = get_config("./hyper_batch/configuration/regions.json")
all_regions = all_regions['regions']
for item in all_regions:
    if item['main_region'] == 'True':
        main_region = item

###############cdk app
#---------------------
app = core.App()

################# main region stacks
#-----------------------------------

####### front-end stack in main region
# THE FRONT-END-STACK IS TURNED OFF BY DEFAULT
# It instead exists in synthesized format as "template.json". It is deployed via HYPER CLI using AWS CLI call to AWS Cloudformation that point to template.json.
# The HYPER CLI will replace parameters in template.json to include user input configurations. If you want to make changes to this stack and re-synthesize
# template.json (use cf-update.py for this) or simply use CDK to deploy it you can turn it on by setting environment parameter "DEPLOYED=False"
try:
    deployed = os.environ.get("DEPLOYED")
    print('DEPLOYED = ' + deployed)
except Exception:
    deployed = 'True'

if deployed == 'False':
    front_end_stack_name = stack_name + '-front-end-' + main_region['region']
    print('Load front-end for main region '+ main_region['region'])
    HyperFrontEnd(app, front_end_stack_name, env=core.Environment(account= account, region=main_region['region']), account=account, stack_name=stack_name, enable_dashboard=enable_dashboard, import_vpc=main_region['import_vpc'], vpc_id=main_region['vpc_id'], cidr=main_region['cidr'])

####### cluster stack in main region
print('Load Clusters for main region '+ main_region['region'])
cluster_stack_name = stack_name + '-clusters-' + main_region['region']
main_region_clusters = Clusters(app, cluster_stack_name, env=core.Environment(account= account, region=main_region['region']), stack_name=stack_name, main_region=main_region['region'], is_main_region=main_region['main_region'],  import_vpc=main_region['import_vpc'], cidr=main_region['cidr'], vpc_id=main_region['vpc_id'], deploy_vpc_endpoints=main_region['deploy_vpc_endpoints'])

####### core stack in main region
main_region_backend_stack_name = stack_name + '-core-' + main_region['region']
print('Load back-end for main region '+ main_region['region'])
HyperBatchCore(app, main_region_backend_stack_name, env=core.Environment(account= account,region=main_region['region']), stack_name=stack_name, main_region=main_region['region'], is_main_region=main_region['main_region'],  import_vpc=main_region['import_vpc'], cidr=main_region['cidr'], vpc_id=main_region['vpc_id'], enable_dashboard=enable_dashboard).add_dependency(main_region_clusters)

####### queue stack in main region
queue_stack_name = stack_name + '-queues-' + main_region['region']
print('Load Queues for main region '+ main_region['region'])
Queues(app, queue_stack_name, env=core.Environment(account= account, region=main_region['region']), main_region=main_region['region'], enable_dashboard=enable_dashboard, stack_name=stack_name).add_dependency(main_region_clusters)

####### task definition stack in main region
print('Load Task Definitions for main region '+ main_region['region'])
taskdef_stack_name = stack_name + '-taskDefinitions-' + main_region['region']
JobDefinitions(app, taskdef_stack_name, env=core.Environment(account= account, region=main_region['region']), is_main_region=main_region['main_region'], stack_name=stack_name).add_dependency(main_region_clusters)

####### images stack in main region
print('Load Images for main region '+ main_region['region'])
image_stack_name = stack_name + '-images-' + main_region['region']
Images(app, image_stack_name, env=core.Environment(account= account, region=main_region['region']), main_region=main_region['region'], stack_name=stack_name)

####### dashboard stack in main region
if enable_dashboard == "True":
    print('Load Dashboard for main region '+ main_region['region'])
    dashboard_stack_name = stack_name + '-dashboard-' + main_region['region']
    Dashboard(app, dashboard_stack_name, env=core.Environment(account= account, region=main_region['region']), stack_name=stack_name).add_dependency(main_region_clusters)


############## hub region stacks
#-----------------------------------

for region in all_regions:
    if region['main_region'] == 'False':
        ####### core stack in hub region
        print('Load Hub Region '+ region['region'])
        hub_name = stack_name + '-core-' + region['region']
        HyperBatchCore(app, hub_name, env=core.Environment(account=account, region=region['region']), stack_name=stack_name, main_region=main_region['region'], is_main_region=region['main_region'],  import_vpc=region['import_vpc'], cidr=region['cidr'], vpc_id=region['vpc_id'], peer_with_main_region=region['peer_with_main_region'], enable_dashboard=enable_dashboard).add_dependency(main_region_clusters)
        
        ####### cluster stack in hub region
        print('Load Clusters for hub region '+ region['region'])
        cluster_stack_name = stack_name + '-clusters-' + region['region']
        Clusters(app, cluster_stack_name, env=core.Environment(account=account, region=region['region']), stack_name=stack_name, main_region=main_region['region'], is_main_region=region['main_region'],  import_vpc=region['import_vpc'], cidr=region['cidr'], vpc_id=region['vpc_id'], peer_with_main_region=region['peer_with_main_region'], deploy_vpc_endpoints=region['deploy_vpc_endpoints']).add_dependency(main_region_clusters)

        ####### task definition stack in hub region
        print('Load Task Definitions for hub region '+ region['region'])
        taskdef_stack_name = stack_name + '-taskDefinitions-' + region['region']
        JobDefinitions(app, taskdef_stack_name, env=core.Environment(account=account, region=region['region']), is_main_region=region['main_region'], stack_name=stack_name).add_dependency(main_region_clusters)

        ####### images stack in main region
        print('Load Images for hub region '+ region['region'])
        image_stack_name = stack_name + '-images-' + region['region']
        Images(app, image_stack_name, env=core.Environment(account=account, region=region['region']), main_region=main_region['region'], stack_name=stack_name)


app.synth()  

