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

import os
import boto3
from aws_xray_sdk.core import patch_all
import logging
import jsonpickle
from dynamodb_json import json_util as ddb_json
import time


LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()


def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    main_region = os.environ.get('MAIN_REGION')

    dynamo = boto3.client('dynamodb', region_name=main_region)

    for record in event.get('Records'):

        if record.get('eventName') in ('MODIFY'):
            data = ddb_json.loads(record['dynamodb']['NewImage'])
            logger.info('## DATA\r' + jsonpickle.encode(data))

            job_id = data['id']
            Status = data['Status']
            Output = data['Output']
            table = data['JobQueue']
            time_stamp = str(data['CurrentTime'])

            if job_id == 'null':
                continue

            retry = 3
            count = 1
            while count <= retry:
                try:
                    res = dynamo.get_item(
                                TableName=table,
                                Key={
                                    'id': {
                                        'S': job_id}},       
                                AttributesToGet=[
                                    'RetriesAvailable',
                                    'Status'
                                ])
                    
                    RetriesAvailable = int(res['Item']['RetriesAvailable']['N'])
                    LastStatus = res['Item']['Status']['S']
                    break
                except:
                    time.sleep(1)
                    logger.error('## No matching job in queue table to update ' + jsonpickle.encode(job_id))
                    if count == retry:
                        raise ValueError('ALL RETRIES FAILED')
                    count += 1
            
            if LastStatus == 'Successful':
                continue
            
            retry = 3
            count = 1
            while count <= retry:
                try:
                    if Status == 'Failed':
                        if RetriesAvailable > 0:
                            NewRetries = RetriesAvailable -1
                            update = dynamo.update_item(
                                TableName=table,
                                Key={'id': {'S': job_id}},
                                UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q, #attr4 = :t",
                                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'RetriesAvailable', '#attr4': 'tRetry'},
                                ExpressionAttributeValues={':p': {'S': str(Status)}, ':r': {'S': str(Output)}, ':q': {'N': str(NewRetries)}, ':t': {'S': time_stamp}},
                                ReturnValues="UPDATED_NEW"
                                )
                            logger.info('## PUT MESSAGE DYNAMODB RESPONSE\r' + jsonpickle.encode(update))
                            break
                        else:
                            update = dynamo.update_item(
                                TableName=table,
                                Key={'id': {'S': job_id}},
                                UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q, #attr4 = :t",
                                ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'RetriesAvailable', '#attr4': 'tFailed'},
                                ExpressionAttributeValues={':p': {'S': str(Status)}, ':r': {'S': str(Output)}, ':q': {'N': str(RetriesAvailable)}, ':t': {'S': time_stamp}},
                                ReturnValues="UPDATED_NEW"
                                )
                            logger.info('## PUT MESSAGE DYNAMODB RESPONSE\r' + jsonpickle.encode(update))
                            break


                    elif Status == 'Running':
                        update = dynamo.update_item(
                                    TableName=table,
                                    Key={'id': {'S': job_id}},
                                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :t",
                                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tRunning'},
                                    ExpressionAttributeValues={':p': {'S': str(Status)}, ':r': {'S': str(Output)}, ':t': {'S': time_stamp}},
                                    ReturnValues="UPDATED_NEW"
                                    )

                        logger.info('## PUT MESSAGE DYNAMODB RESPONSE\r' + jsonpickle.encode(update))
                        break

                    elif Status == "Successful":
                        update = dynamo.update_item(
                                    TableName=table,
                                    Key={'id': {'S': job_id}},
                                    UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :t",
                                    ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'tSuccessful'},
                                    ExpressionAttributeValues={':p': {'S': str(Status)}, ':r': {'S': str(Output)}, ':t': {'S': time_stamp}},
                                    ReturnValues="UPDATED_NEW"
                                    )

                        logger.info('## PUT MESSAGE DYNAMODB RESPONSE\r' + jsonpickle.encode(update))
                        break
                    else:
                        logger.error('## UNHANDLED STATUS\r' + jsonpickle.encode(data))
                        break
                    break
                except Exception:
                    time.sleep(1)
                    logger.error('## Failed to update main region queue table for: \r' + jsonpickle.encode(data))
                    if count == retry:
                        raise ValueError('ALL RETRIES FAILED')
                    count += 1