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
import os
from aws_xray_sdk.core import patch_all
import logging
import jsonpickle
from datetime import datetime
import json


LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

region = os.environ.get('REGION')
main_region = os.environ.get('MAIN_REGION')

stack_name = os.environ.get("STACK_NAME")

kinesis = boto3.client('kinesis', region_name=region)

boto3.resource('dynamodb', region_name=region)
deser = boto3.dynamodb.types.TypeDeserializer()

def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))
   
    count = 0
    logs = []
    queue = None
    for record in event['Records']:

        if record.get('eventName') in ('INSERT', 'MODIFY'):

            item = {k: deser.deserialize(v) for k,v in record['dynamodb']['NewImage'].items()}
            item.pop('Output')
            item.pop('commands')

            queue = record['dynamodb']['NewImage']['jobQueue']['S']
            if record['dynamodb']['NewImage']['Status']['S'] == 'Waiting':
                time_stamp = record['dynamodb']['NewImage']['tCreated']['S']
            elif record['dynamodb']['NewImage']['Status']['S'] == 'Running':
                time_stamp = record['dynamodb']['NewImage']['tRunning']['S']
            elif record['dynamodb']['NewImage']['Status']['S'] == 'Successful':
                time_stamp = record['dynamodb']['NewImage']['tSuccessful']['S']
            elif record['dynamodb']['NewImage']['Status']['S'] == 'Failed':
                if int(record['dynamodb']['NewImage']['RetriesAvailable']['N']) > 0:
                    time_stamp = record['dynamodb']['NewImage']['tRetry']['S']
                else:
                    time_stamp = record['dynamodb']['NewImage']['tFailed']['S']
            elif 'tERROR' in record['dynamodb']['NewImage']:
                time_stamp = record['dynamodb']['NewImage']['tERROR']['S']
            else:
                time_stamp = datetime.now().isoformat()

            logs.append({'time_stamp': time_stamp, 'log_type': 'SYSTEM', 'id': record['dynamodb']['NewImage']['id']['S'], 'jobDefinition': record['dynamodb']['NewImage']['jobDefinition']['S'], 'jobQueue': queue, 'data': item})
            count += 1
    
    if not queue == None:
        kinesis.put_record(
            StreamName=stack_name + '_log_stream',
            Data=bytes(json.dumps(logs, default=str), 'utf-8'),
            PartitionKey=queue
        )

    return str(count) + ' records processed.'

