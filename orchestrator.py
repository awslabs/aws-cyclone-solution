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

from contextlib import nullcontext
import decimal
import boto3
import csv, sys, time, argparse
from datetime import datetime
import json
import os
import sys
import time
import urllib3
import json
import uuid
import subprocess
from subprocess import Popen, PIPE
from subprocess import check_output
import logging
import jsonpickle

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.INFO)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)


region = os.environ.get("REGION")
stack_name = os.environ.get("STACK_NAME")
account = os.environ.get("ACCOUNT")

ssm = boto3.client('ssm', region_name=region)
dynamo = boto3.client('dynamodb', region_name=region)
s3 = boto3.client('s3', region_name=region)
s3_r = boto3.resource('s3', region_name=region)

boto3.resource('dynamodb', region_name=region)
deser = boto3.dynamodb.types.TypeDeserializer()


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

def clean_item(item):
    item = {k: deser.deserialize(v) for k,v in item.items()}
    item.pop('Output_Log')

    item = replace_decimals(item)
    try:
        item = json.loads(item)
    except Exception:
        pass
    try:
        for k, v in item.items():
            try:
                loaded = json.loads(v)
                item[k] = loaded
            except Exception:
                pass
    except Exception:
        pass
    try:
        for k, v in item.items():
            if v == '':
                item[k] = None
    except Exception:
        pass

    return item

def do_work(command_list):
    try:
        output = []
        if len(command_list) < 1:
            status = 'FAILED'
            output = 'Nothing to deploy, are one or more regions specified?'
            logger.error('## PROCESS FAILED: ' + jsonpickle.encode(status, output))
            return output, status
        for command in command_list:
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if 'returncode=0' in str(result):
                status = 'ACTIVE'
                output.append(result)
            else:
                status = 'FAILED'
                output.append(result)
                return output, status
        logger.info('## PROCESS STATUS: ' + jsonpickle.encode(status, output))
        return output, status
    except subprocess.CalledProcessError as e:
        result = 'FAILED ' + str(e)
        status = 'FAILED'
        logger.error('## PROCESS FAILED: ' + jsonpickle.encode(status, result))
        return result, status

def replace_decimals(obj):
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_decimals(obj[i])
        return obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = replace_decimals(obj[k])
        return obj
    elif isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return float(obj)
        else:
            return float(obj)
    else:
        return obj

def create_region(stack_name, region):
    command1 = 'cdk bootstrap aws://{}/{}'.format(account, region)
    command2 = 'cdk deploy {}-core-{}'.format(stack_name, region)
    command3 = 'cdk deploy {}-clusters-{}'.format(stack_name, region)
    command4 = 'cdk deploy {}-taskDefinitions-{}'.format(stack_name, region)
    command5 = 'cdk deploy {}-images-{}'.format(stack_name, region)
    command = [command1, command2, command3, command4, command5]
    result, status = do_work(command)

    return result, status

def create_region_with_dash(stack_name, region):
    command1 = 'cdk bootstrap aws://{}/{}'.format(account, region)
    command2 = 'cdk deploy {}-core-{}'.format(stack_name, region)
    command3 = 'cdk deploy {}-clusters-{}'.format(stack_name, region)
    command4 = 'cdk deploy {}-taskDefinitions-{}'.format(stack_name, region)
    command5 = 'cdk deploy {}-images-{}'.format(stack_name, region)
    command6 = 'cdk deploy {}-dashboard-{}'.format(stack_name, region)
    command = [command1, command2, command3, command4, command5, command6]
    result, status = do_work(command)

    return result, status

def update_region(stack_name, region):
    command2 = 'cdk deploy "*{}"'.format(region)
    command = [command2]
    result, status = do_work(command)

    return result, status

def delete_region(region):
    command2 = 'cdk destroy "*{}" --force'.format(region)
    command = [command2]
    result, status = do_work(command)

    return result, status

def update_clusters(stack_name):
    all_regions = get_config("./hyper_batch/configuration/regions.json")
    all_regions = all_regions['regions']
    commands = []
    for region in all_regions:
        command = 'cdk deploy {}-clusters-{}'.format(stack_name, region['region'])
        commands.append(command)
    result, status = do_work(commands)

    return result, status


def update_queues(stack_name, main_region):
    command = 'cdk deploy {}-queues-{}'.format(stack_name, main_region)
    command = [command]
    result, status = do_work(command)
    
    return result, status

def update_jobDefinitions(stack_name):
    all_regions = get_config("./hyper_batch/configuration/regions.json")
    all_regions = all_regions['regions']
    commands = []
    for region in all_regions:
        command = 'cdk deploy {}-taskDefinitions-{}'.format(stack_name, region['region'])
        commands.append(command)
    result, status = do_work(commands)
    
    return result, status
def update_images(stack_name):
    all_regions = get_config("./hyper_batch/configuration/regions.json")
    all_regions = all_regions['regions']
    commands = []
    for region in all_regions:
        command = 'cdk deploy {}-images-{}'.format(stack_name, region['region'])
        commands.append(command)
    result, status = do_work(commands)
    
    return result, status

##############configure settings from parameter store and env variables from cf stack input

enable_dashboard = ssm.get_parameter(
        Name=str(stack_name + '_enable_dashboard'))

settings = {
                "stack_settings":
                    {
                        "stack_name": stack_name,
                        "account": account,
                        "enable_dashboard": enable_dashboard['Parameter']['Value']
                    }
            }
with open("./hyper_batch/configuration/settings.json", 'w') as outfile:
    json.dump(settings, outfile)

logger.info('## CREATED setting.json file : ' + jsonpickle.encode(settings))

#########empty config files
regions = {}
regions['regions'] = []
with open("./hyper_batch/configuration/regions.json", 'w') as outfile:
        json.dump(regions, outfile)
        
clusters = {}
clusters['clusters'] = []
with open("./hyper_batch/configuration/clusters.json", 'w') as outfile:
    json.dump(clusters, outfile)

queues = {}
queues['queues'] = []
with open("./hyper_batch/configuration/queues.json", 'w') as outfile:
    json.dump(queues, outfile)

jobDefinitions = {}
jobDefinitions['jobDefinitions'] = []
with open("./hyper_batch/configuration/job_definitions.json", 'w') as outfile:
    json.dump(jobDefinitions, outfile)

images = {}
images['images'] = []
with open("./hyper_batch/configuration/images.json", 'w') as outfile:
        json.dump(images, outfile)

def scan_regions():
    dynamo_regions = dynamo.scan(
        TableName=stack_name + '_regions_table',
    )

    dynamo_regions = dynamo_regions['Items']
    logger.info('## CHECK REGIONS : ' + jsonpickle.encode(dynamo_regions))


    regions = {}
    regions['regions'] = []
    failed = []
    count = 0
    for item in dynamo_regions:
        try:
            local_item = clean_item(item)
            local_item['region'] = local_item['name']
            regions['regions'].append(local_item)
        except Exception as e:
            logger.error('## FAILED TO PARSE DATA: ' + jsonpickle.encode(e, item))
            update1 = dynamo.update_item(
                TableName=stack_name + '_regions_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': 'FAILED'}, ':r': {'S': str('FAILED ' + str(e))}},
                ReturnValues="UPDATED_NEW"
                )
            failed.append(count)
            pass
        count =+ 1
    
    for item in failed:
        dynamo_regions.pop(item)

    with open("./hyper_batch/configuration/regions.json", 'w') as outfile:
        json.dump(regions, outfile)
    
    return dynamo_regions, regions

def scan_clusters():
    dynamo_clusters = dynamo.scan(
        TableName=stack_name + '_clusters_table',
    )

    dynamo_clusters = dynamo_clusters['Items']

    logger.info('## CHECK CLUSTERS : ' + jsonpickle.encode(dynamo_clusters))

    clusters = {}
    clusters['clusters'] = []
    failed = []
    count = 0
    for item in dynamo_clusters:
        try:
            local_item = clean_item(item)
            local_item['clusterName'] = local_item['name']
            clusters['clusters'].append(local_item)
        except Exception as e:
            logger.error('## FAILED TO PARSE DATA: ' + jsonpickle.encode(e, item))
            update1 = dynamo.update_item(
                TableName=stack_name + '_clusters_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': 'FAILED'}, ':r': {'S': str('FAILED ' + str(e))}},
                ReturnValues="UPDATED_NEW"
                )
            failed.append(count)
            pass
        count =+ 1
    
    for item in failed:
        dynamo_clusters.pop(item)

    with open("./hyper_batch/configuration/clusters.json", 'w') as outfile:
        json.dump(clusters, outfile)

    return dynamo_clusters, clusters

def scan_definitions():
    ddb_response = dynamo.scan(
        TableName=stack_name + '_jobDefinitions_table',
    )

    dynamo_jobDefinitions = ddb_response['Items']
    while "LastEvaluatedKey" in ddb_response:
        ddb_response = dynamo.scan(TableName=stack_name + '_jobDefinitions_table', ExclusiveStartKey=ddb_response["LastEvaluatedKey"])
        dynamo_jobDefinitions.extend(ddb_response["Items"])

    logger.info('## CHECK JOB DEFINITIONS : ' + jsonpickle.encode(dynamo_jobDefinitions))
    
    jobDefinitions = {}
    jobDefinitions['jobDefinitions'] = []
    failed =[]
    count = 0
    for raw_item in dynamo_jobDefinitions:
        try:
            item = clean_item(raw_item)

            remove = []
            for k,v in item.items():
                if k == 'privileged':
                    if v == 'False' or v == 'false':
                        item[k] = False
                    if v == 'True' or v == 'true':
                        item[k] = True
                if k == 'JOBStoWORKERSratio':
                    item[k] = int(v)
                    continue
                try:
                    item[k] = float(v)
                except Exception:
                    pass
            
            local_item = item
            local_item['jobDefinitionName'] = item.get('name', None)
            jobDefinitions['jobDefinitions'].append(local_item)
        except Exception as e:
            logger.error('## FAILED TO PARSE DATA: ' + jsonpickle.encode(e, raw_item))
            update1 = dynamo.update_item(
                TableName=stack_name + '_jobDefinitions_table',
                Key={'name': {'S': raw_item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': 'FAILED'}, ':r': {'S': str('FAILED ' + str(e))}},
                ReturnValues="UPDATED_NEW"
                )
            failed.append(count)
            pass
        count =+ 1
    
    for item in failed:
        dynamo_jobDefinitions.pop(item)

    with open("./hyper_batch/configuration/job_definitions.json", 'w') as outfile:
        json.dump(jobDefinitions, outfile)
    
    return dynamo_jobDefinitions, jobDefinitions

def scan_queues():
    dynamo_queues = dynamo.scan(
        TableName=stack_name + '_queues_table',
    )

    dynamo_queues = dynamo_queues['Items']

    logger.info('## CHECK QUEUES : ' + jsonpickle.encode(dynamo_queues))

    queues = {}
    queues['queues'] = []
    failed = []
    count = 0
    for item in dynamo_queues:
        try:
            local_item = clean_item(item)
            local_item['queue_name'] = local_item['name']
            queues['queues'].append(local_item)
        except Exception as e:
            logger.error('## FAILED TO PARSE DATA: ' + jsonpickle.encode(e, item))
            update1 = dynamo.update_item(
                TableName=stack_name + '_queues_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': 'FAILED'}, ':r': {'S': str('FAILED ' + str(e))}},
                ReturnValues="UPDATED_NEW"
                )
            failed.append(count)
            pass
        count =+ 1
    
    for item in failed:
        dynamo_queues.pop(item)

    with open("./hyper_batch/configuration/queues.json", 'w') as outfile:
        json.dump(queues, outfile)
    
    return dynamo_queues, queues

def scan_images():

    result, status = do_work(['aws s3 sync s3://{}-images-{}/images ./hyper_batch/configuration/images'.format(stack_name, region)])

    dynamo_images = dynamo.scan(
        TableName=stack_name + '_images_table',
    )

    dynamo_images = dynamo_images['Items']

    logger.info('## CHECK IMAGES : ' + jsonpickle.encode(dynamo_images))
    
    images = {}
    images['images'] = []
    failed =[]
    count = 0
    for raw_item in dynamo_images:
        try:
            local_item = clean_item(raw_item)
            local_item['imageName'] = local_item['name']
            local_item['directory'] = 'hyper_batch/configuration/images/{}'.format(local_item.get('name', None))
            images['images'].append(local_item)
        except Exception as e:
            logger.error('## FAILED TO PARSE DATA: ' + jsonpickle.encode(e, raw_item))
            update1 = dynamo.update_item(
                TableName=stack_name + '_images_table',
                Key={'name': {'S': raw_item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': 'FAILED'}, ':r': {'S': str('FAILED ' + str(e))}},
                ReturnValues="UPDATED_NEW"
                )
            failed.append(count)
            pass
        count =+ 1
    
    for item in failed:
        dynamo_images.pop(item)

    with open("./hyper_batch/configuration/images.json", 'w') as outfile:
        json.dump(images, outfile)
    
    return dynamo_images, images


for i in range(0,29,1):

    ####################################### SCAN ALL CONFIGURATIONS AND UPDATE LOCAL CONFIG TABLES
    dynamo_regions, regions = scan_regions()
    dynamo_clusters, clusters = scan_clusters()
    dynamo_queues, queues = scan_queues()
    dynamo_jobDefinitions, jobDefinitions = scan_definitions()
    dynamo_images, images = scan_images()

    ####################regions deploy
    for item in dynamo_regions:

        if item['Status']['S'] == 'Creating':
            logger.info('## CREATING: ' + jsonpickle.encode(item))
            if enable_dashboard['Parameter']['Value'] == 'True' and item['main_region']['S'] == 'True':
                result, status = create_region_with_dash(stack_name=stack_name, region=item['name']['S'])
            else:
                result, status = create_region(stack_name=stack_name, region=item['name']['S'])

            logger.info('## Output : ' + jsonpickle.encode(result, status))

            update1 = dynamo.update_item(
                TableName=stack_name + '_regions_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                ReturnValues="UPDATED_NEW"
                )

        if item['Status']['S'] == 'Updating':
            result, status = update_region(stack_name=stack_name, region=item['name']['S'])

            update1 = dynamo.update_item(
                TableName=stack_name + '_regions_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                ReturnValues="UPDATED_NEW"
                )

        if item['Status']['S'] == 'Deleting':
            logger.info('## DELETING: ' + jsonpickle.encode(item))
            result, status = delete_region(region=item['name']['S'])

            if status == 'ACTIVE':
                update1 = dynamo.delete_item(
                    TableName=stack_name + '_regions_table',
                    Key={'name': {'S': item['name']['S']}}
                    )
            else:
                update1 = dynamo.update_item(
                    TableName=stack_name + '_regions_table',
                    Key={'name': {'S': item['name']['S']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                    ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                    ReturnValues="UPDATED_NEW"
                    )
    print('REGIONS UPDATED')

    ####################clusters deploy
    for item in dynamo_clusters:
        
        if item['Status']['S'] == 'Creating' or item['Status']['S'] == 'Updating':
            logger.info('## CREATING: ' + jsonpickle.encode(item))

            result, status = update_clusters(stack_name=stack_name)

            update1 = dynamo.update_item(
                TableName=stack_name + '_clusters_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                ReturnValues="UPDATED_NEW"
                )

        if item['Status']['S'] == 'Deleting':
            logger.info('## DELETING: ' + jsonpickle.encode(item))
            new_clusters ={}
            new_clusters['clusters'] = []
            for cluster in clusters['clusters']:
                if item['name']['S'] == cluster['clusterName']:
                    print('not including cluster for deletion')
                else:
                    new_clusters['clusters'].append(cluster)
            
            with open("./hyper_batch/configuration/clusters.json", 'w') as outfile:
                json.dump(new_clusters, outfile)

            result, status = update_clusters(stack_name=stack_name)

            if status == 'ACTIVE':
                update1 = dynamo.delete_item(
                    TableName=stack_name + '_clusters_table',
                    Key={'name': {'S': item['name']['S']}}
                    )

            else:
                with open("./hyper_batch/configuration/clusters.json", 'w') as outfile:
                    json.dump(clusters, outfile)


                update1 = dynamo.update_item(
                    TableName=stack_name + '_clusters_table',
                    Key={'name': {'S': item['name']['S']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                    ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                    ReturnValues="UPDATED_NEW"
                    )

    print('CLUSTERS UPDATED')


####################queues deploy
    for item in dynamo_queues:
        
        if item['Status']['S'] == 'Creating' or item['Status']['S'] == 'Updating':
            logger.info('## CREATING: ' + jsonpickle.encode(item))
            result, status = update_queues(stack_name=stack_name, main_region=region)

            update1 = dynamo.update_item(
                TableName=stack_name + '_queues_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                ReturnValues="UPDATED_NEW"
                )

        if item['Status']['S'] == 'Deleting':
            logger.info('## DELETING: ' + jsonpickle.encode(item))
            new_queues ={}
            new_queues['queues'] = []
            for queue in queues['queues']:
                if item['name']['S'] == queue['queue_name']:
                    print('Removing Cluster for deletion from config')
                else:
                    new_queues['queues'].append(queue)
            
            with open("./hyper_batch/configuration/queues.json", 'w') as outfile:
                json.dump(new_queues, outfile)

            result, status = update_queues(stack_name=stack_name, main_region=region)

            if status == 'ACTIVE':
                update1 = dynamo.delete_item(
                    TableName=stack_name + '_queues_table',
                    Key={'name': {'S': item['name']['S']}}
                    )

            else:
                with open("./hyper_batch/configuration/queues.json", 'w') as outfile:
                    json.dump(queues, outfile)


                update1 = dynamo.update_item(
                    TableName=stack_name + '_queues_table',
                    Key={'name': {'S': item['name']['S']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                    ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                    ReturnValues="UPDATED_NEW"
                    )

    print('QUEUES UPDATED')

    ####################jobDefinitions deploy
    for item in dynamo_jobDefinitions:
        
        if item['Status']['S'] == 'Creating' or item['Status']['S'] == 'Updating':
            logger.info('## CREATING: ' + jsonpickle.encode(item))

            result, status = update_jobDefinitions(stack_name=stack_name)

            update1 = dynamo.update_item(
                TableName=stack_name + '_jobDefinitions_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                ReturnValues="UPDATED_NEW"
                )

        if item['Status']['S'] == 'Deleting':
            logger.info('## DELETING: ' + jsonpickle.encode(item))
            new_jobDefinitions ={}
            new_jobDefinitions['jobDefinitions'] = []
            for jobDefinition in jobDefinitions['jobDefinitions']:
                if item['name']['S'] == jobDefinition['jobDefinitionName']:
                    print('Removing cluster to be deleted from config')
                else:
                    new_jobDefinitions['jobDefinitions'].append(jobDefinition)
            
            with open("./hyper_batch/configuration/job_definitions.json", 'w') as outfile:
                json.dump(new_jobDefinitions, outfile)

            result, status = update_jobDefinitions(stack_name=stack_name)

            if status == 'ACTIVE':
                update1 = dynamo.delete_item(
                    TableName=stack_name + '_jobDefinitions_table',
                    Key={'name': {'S': item['name']['S']}}
                    )

            else:
                with open("./hyper_batch/configuration/job_definitions.json", 'w') as outfile:
                    json.dump(jobDefinitions, outfile)

                update1 = dynamo.update_item(
                    TableName=stack_name + '_jobDefinitions_table',
                    Key={'name': {'S': item['name']['S']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                    ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                    ReturnValues="UPDATED_NEW"
                    )

    print('JOB DEFINITIONS UPDATED')

    ####################images deploy
    for item in dynamo_images:
        
        if item['Status']['S'] == 'Creating' or item['Status']['S'] == 'Updating':
            logger.info('## CREATING: ' + jsonpickle.encode(item))
            result, status = update_images(stack_name=stack_name)

            update1 = dynamo.update_item(
                TableName=stack_name + '_images_table',
                Key={'name': {'S': item['name']['S']}},
                UpdateExpression="set #attr1 = :p, #attr2 = :r",
                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                ReturnValues="UPDATED_NEW"
                )

        if item['Status']['S'] == 'Deleting':
            logger.info('## DELETING: ' + jsonpickle.encode(item))
            new_images ={}
            new_images['images'] = []
            for image in images['images']:
                if item['name']['S'] == image['imageName']:
                    print('Removing cluster to be deleted from config')
                else:
                    new_images['images'].append(image)
            
            with open("./hyper_batch/configuration/images.json", 'w') as outfile:
                json.dump(new_images, outfile)

            result, status = update_images(stack_name=stack_name)

            if status == 'ACTIVE':
                update1 = dynamo.delete_item(
                    TableName=stack_name + '_images_table',
                    Key={'name': {'S': item['name']['S']}}
                    )

            else:
                with open("./hyper_batch/configuration/images.json", 'w') as outfile:
                    json.dump(images, outfile)


                update1 = dynamo.update_item(
                    TableName=stack_name + '_images_table',
                    Key={'name': {'S': item['name']['S']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output_Log'},
                    ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(result)}},
                    ReturnValues="UPDATED_NEW"
                    )
    print('IMAGES UPDATED')
    logger.info('## WAITING 10 SECONDS')
    time.sleep(10)
