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
import random
from dynamodb_json import json_util as ddb_json
import time
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    region_weights = os.environ.get('REGION_DISTRIBUTION_WEIGHTS')
    delivery_stream_name = os.environ.get('CLUSTER_MAPPING')
    main_region = os.environ.get('MAIN_REGION')
    
    region_weights = region_weights.replace("{", "").replace("}", "").replace(" ","").replace("'","").replace('"','').split(",")
            
    dictionary = {}

    for i in region_weights:
        dictionary[i.split(":")[0].strip('\'').replace("\"", "")] = i.split(":")[1].strip('"\'')

    region_weights = dictionary

    rotation_regions = []
    for key in dictionary:
        for i in range(int(region_weights[key])):
            rotation_regions.append(key)

    logger.info('## Region rotation\r' + jsonpickle.encode(rotation_regions))

    #kinesis = boto3.client('kinesis')
    dynamo = boto3.client('dynamodb', region_name=main_region)
    sqs = boto3.resource('sqs', region_name=main_region)

    c = random.randint(0, len(rotation_regions))
    for record in event.get('Records'):
        
        if record.get('eventName') in ('INSERT', 'MODIFY'):
            data = ddb_json.loads(record['dynamodb']['NewImage'])
            status = data['Status']

            try:
                region = rotation_regions[c]
            except Exception:
                c = 0
                region = rotation_regions[c]

            retry = 3
            count = 1
            while count <= retry:
                try:
                    if status == 'Waiting':
                        logger.info('## DATA\r' + jsonpickle.encode(data))
                        queue_name = data['jobDefinition']
                        c = c+1 
                        try:
                            queue = sqs.get_queue_by_name(QueueName=queue_name)
                            # Send a new job message to sqs
                            sqs_response = queue.send_message(MessageBody=jsonpickle.encode(data))
                        except Exception as e:
                            error = 'ERROR Could not send to task definition queue: ' + queue_name
                            update = dynamo.update_item(
                                TableName=data['jobQueue'],
                                Key={'id': {'S': data['id']}},
                                UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                                ExpressionAttributeValues={':p': {'S': str(error)}, ':r': {'S': str(e)}, ':q': {'S': datetime.now().isoformat()}},
                                ReturnValues="UPDATED_NEW"
                                )
                            raise ValueError(e)
                        
                        try:
                            # Send to kinesis (should change to firehose)
                            kinesis = boto3.client('kinesis', region_name=region)

                            kinesis_response = kinesis.put_record(
                                StreamName=delivery_stream_name,
                                Data=bytes(json.dumps(data, default=str), 'utf-8'),
                                PartitionKey=data['jobDefinition']
                            )
                        except Exception as e:
                            error = 'ERROR Failed to request worker from cluster: ' + delivery_stream_name
                            update = dynamo.update_item(
                                TableName=data['jobQueue'],
                                Key={'id': {'S': data['id']}},
                                UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                                ExpressionAttributeValues={':p': {'S': str(error)}, ':r': {'S': str(e)}, ':q': {'S': datetime.now().isoformat()}},
                                ReturnValues="UPDATED_NEW"
                                )
                            raise ValueError(e)

                        logger.info('## JOB_ID\r' + jsonpickle.encode(data['id']) + '## SEND MESSAGES SQS RESPONSE\r' + jsonpickle.encode(sqs_response) + '## PUT RECORD BATCH RESPONSE\r' + jsonpickle.encode(kinesis_response))
                        break
                    elif status == 'Failed':
                        retries = data['RetriesAvailable']
                        if retries > 0:
                            logger.info('## DATA\r' + jsonpickle.encode(data))
                            queue_name = data['jobDefinition']
                            c = c+1 
                            try:
                                queue = sqs.get_queue_by_name(QueueName=queue_name)
                                # Send a new job message to sqs
                                sqs_response = queue.send_message(MessageBody=jsonpickle.encode(data))
                            except Exception as e:
                                error = 'ERROR Could not send to task definition queue: ' + queue_name
                                update = dynamo.update_item(
                                    TableName=data['jobQueue'],
                                    Key={'id': {'S': data['id']}},
                                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                                    ExpressionAttributeValues={':p': {'S': str(error)}, ':r': {'S': str(e)}, ':q': {'S': datetime.now().isoformat()}},
                                    ReturnValues="UPDATED_NEW"
                                    )
                                raise ValueError(e)
                            
                            try:
                                # Send to kinesis (should change to firehose)
                                kinesis = boto3.client('kinesis', region_name=region)
                                kinesis_response = kinesis.put_record(
                                    StreamName=delivery_stream_name,
                                    Data=bytes(json.dumps(data, default=str), 'utf-8'),
                                    PartitionKey=data['jobDefinition']
                                )
                            except Exception as e:
                                error = 'ERROR Failed to request worker from cluster: ' + delivery_stream_name
                                update = dynamo.update_item(
                                    TableName=data['jobQueue'],
                                    Key={'id': {'S': data['id']}},
                                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tERROR'},
                                    ExpressionAttributeValues={':p': {'S': str(error)}, ':r': {'S': str(e)}, ':q': {'S': datetime.now().isoformat()}},
                                    ReturnValues="UPDATED_NEW"
                                    )
                                raise ValueError(e)
                            break
                        break
                    break
                except Exception as e:
                    time.sleep(1)
                    logger.error('## Failed to forward resource request\r' + jsonpickle.encode(e))
                    if count == retry:
                        raise ValueError('ALL RETRIES FAILED')
                    count += 1

    return