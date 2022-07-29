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
import boto3
from aws_xray_sdk.core import patch_all
import logging
import jsonpickle
import base64
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()


def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    batchProcessingJobQueue =  os.environ.get("BATCH_JOB_QUEUE")
    region = os.environ.get("REGION")
    stack_name = os.environ.get("STACK_NAME")
    main_region = os.environ.get('MAIN_REGION')

    batch = boto3.client('batch')
    ssm = boto3.client('ssm')
    dynamo = boto3.client('dynamodb', region_name=main_region)
    
    worker_script_s3_location =  's3://' + os.environ.get("WORKER_SCRIPT_S3KEY")

    sf_arn_res = ssm.get_parameter(
            Name=str(stack_name + '-SF-ARN'),
        )
    table_res = ssm.get_parameter(
        Name=str(stack_name + '-table'),
    )

    async_table = table_res['Parameter']['Value']
    sf_arn = sf_arn_res['Parameter']['Value']

    full_list =[]
    id_dict = {}
    for record in event.get("Records"):
        # Kinesis data is base64 encoded so decode here
        message_str = base64.b64decode(record['kinesis']['data']).decode("utf-8")
        message = json.loads(message_str)
        logger.info('## KINESIS MESSAGE\r' + jsonpickle.encode(message))
        jd_queue_string = message['jobDefinition'] + '__H__' + message['jobQueue']
        full_list.append(jd_queue_string)
        if not jd_queue_string in id_dict:
            id_dict[jd_queue_string] = []
        id_dict[jd_queue_string].append({'id': message['id'], 'jobName':message['jobName']})
    
    dedup_list = list(dict.fromkeys(full_list))

    for item in dedup_list:

        job_def, queue = item.split('__H__')
        
        commands = ["./start.sh", worker_script_s3_location, sf_arn, async_table, job_def, region, main_region, stack_name]

        container_overrides = {
            "command": commands
            }
        
        response = ssm.get_parameter(
            Name=job_def,
        )
        try:
            JOBStoWORKERSratio =  response['Parameter']['Value']
            num = full_list.count(item)
            print(num)
            divide = float(JOBStoWORKERSratio)
            print(divide)
            num = round(num/divide + 0.4999999999)
        except Exception as e:
            error = 'ERROR Failed to determine JobstoWorkersRatio reduction for: ' + job_def + ' in ' + region + ' '
            logger.error(error + jsonpickle.encode(e))
            now = datetime.now().isoformat()
            for task in id_dict[item]:
                dynamo.update_item(
                    TableName=queue,
                    Key={'id': {'S': task['id']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                    ExpressionAttributeValues={':p': {'S': str(error)}, ':r': {'S': str(e)}, ':q': {'S': now}},
                    ReturnValues="UPDATED_NEW"
                    )
            raise ValueError(e)

        try:
            if num >= 2:
                array = {"size": num}
                batchResponse = batch.submit_job(jobName=item, 
                                                    jobQueue=batchProcessingJobQueue, 
                                                    jobDefinition=job_def,
                                                    containerOverrides=container_overrides,
                                                    arrayProperties=array,
                                                    tags={'jobQueue': queue}
                                                    )
            elif num == 1:
                batchResponse = batch.submit_job(jobName=item, 
                                                    jobQueue=batchProcessingJobQueue, 
                                                    jobDefinition=job_def,
                                                    containerOverrides=container_overrides,
                                                    tags={'jobQueue': queue}
                                                    )
        except Exception as e:
            error = 'ERROR Failed to submit worker request to: ' + batchProcessingJobQueue + ' ' + region
            logger.error(error + jsonpickle.encode(e))
            now = datetime.now().isoformat()
            for task in id_dict[item]:
                dynamo.update_item(
                    TableName=queue,
                    Key={'id': {'S': task['id']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                    ExpressionAttributeValues={':p': {'S': str(error)}, ':r': {'S': str(e)}, ':q': {'S': now}},
                    ReturnValues="UPDATED_NEW"
                    )
            raise ValueError(e)

    logger.info('## BATCH SUBMIT JOB RESPONSE\r' + jsonpickle.encode(batchResponse))
    
    return True
