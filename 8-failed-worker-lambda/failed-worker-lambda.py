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

import boto3
from boto3.dynamodb.conditions import Key
import os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import logging
from datetime import datetime
import json
import jsonpickle


LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

main_region = os.environ.get('MAIN_REGION')

dynamo_r = boto3.resource('dynamodb', region_name=main_region)
dynamo_c = boto3.client('dynamodb', region_name=main_region)
def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    now = datetime.now().isoformat()

    del context
    if event["source"] != "aws.batch":
        raise ValueError("Function only supports input from events with a source type of: aws.batch")

    jobName = event['detail']['jobName']
    job_def, queue = jobName.split('__H__')

    table = dynamo_r.Table(queue)
    
    response = table.query(
        IndexName='index_jobDefinition',
        KeyConditionExpression=Key('jobDefinition').eq(job_def)
    )

    for item in response['Items']:
        if item['Status'] == 'Waiting':
            dynamo_c.update_item(
                    TableName=queue,
                    Key={'id': {'S': item['id']}},
                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                    ExpressionAttributeValues={':p': {'S': 'One or more workers failed, task may still run'}, ':r': {'S': json.dumps(event, indent=4, sort_keys=True)}, ':q': {'S': now}},
                    ReturnValues="UPDATED_NEW"
                    )
    
    return event






    


