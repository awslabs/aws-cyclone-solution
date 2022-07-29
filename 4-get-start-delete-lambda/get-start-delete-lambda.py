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
import time
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

main_region = os.environ.get('MAIN_REGION')

SQS = boto3.client("sqs", region_name=main_region)
dynamo = boto3.client('dynamodb')

def get_job(event):
    """
    Lambda handler
    """

    queue_url = SQS.get_queue_url(QueueName=event["Input"]["sqs_name"])

    response = SQS.receive_message(
        QueueUrl=queue_url["QueueUrl"],

        AttributeNames=[
            "SentTimestamp"
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            "All"
        ],
        VisibilityTimeout=5,
        WaitTimeSeconds=0,
    )

    try:
        message = response["Messages"][0]
    except (KeyError, IndexError) as err:
        logger.error('## Failed to pull job from sqs:\r' + jsonpickle.encode(response))
        raise err

    logger.info('## GOT_JOB_SQS\r' + jsonpickle.encode(message))
    return message


def extract_job(event):
    """
    Lambda handler
    """

    message = json.loads(event["Body"])
    logger.info('## message for parsing\r' + jsonpickle.encode(message))

    job_details = {
        "job_id": message['id'],
        "commands": message['commands'],
        "queue": message['jobQueue']
    }
    logger.info('## EXTRACT_JOB_DETAILS\r' + jsonpickle.encode(job_details))

    return job_details


def grid_start_job(event):
    logger.info('## EVENT\r' + jsonpickle.encode(event))
 
    response = dynamo.update_item(
        TableName=event['Input']['table'],
        Key={'uuid': {'S': event['Input']['uuid']}},
        UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q, #attr4 = :s, #attr5 = :t, #attr6 = :u, #attr7 = :v, #attr8 = :x",
        ExpressionAttributeNames={'#attr1': 'command', '#attr2': 'LeaveRunning', '#attr3': 'Callback', '#attr4': 'id', '#attr5': 'CurrentTime', '#attr6': 'JobQueue', '#attr7': 'Output', '#attr8': 'Status'},
        ExpressionAttributeValues={':p': {'S': str(event['job_details']['commands'])}, ':r': {'S': str(event['Input']['LeaveRunning'])}, ':q': {'S': str(event['TaskToken'])}, ':s': {'S': str(event['job_details']['job_id'])}, ':t': {'S': datetime.now().isoformat()}, ':u': {'S': str(event['job_details']['queue'])}, ':v': {'S': str('null')}, ':x': {'S': str('Starting')}},
        ReturnValues="UPDATED_NEW"
        )
    logger.info('## DYNAMO_RESPONSE\r' + jsonpickle.encode(response))

    return response
    

def delete_job(event):
    """
    Lambda handler
    """

    queue_url = SQS.get_queue_url(QueueName=event["Input"]["sqs_name"])


    return SQS.delete_message(
        QueueUrl=queue_url["QueueUrl"],
        ReceiptHandle=event["raw_message"]["ReceiptHandle"],
    )


def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    token = event['TaskToken']

    #get job
    retry = 3
    count = 1
    while count <= retry:
        try:
            event['raw_message'] = get_job(event)
            break
        except:
            time.sleep(1)
            if count == retry:
                job_details = {
                    "job_id": "null",
                    "commands": "null",
                    "queue": "null"
                }

                event['Input']['LeaveRunning'] = 'False'
                event['job_details'] = job_details
                event['DynamoDBResponse'] = grid_start_job(event)
                logger.info('## GET_JOB\r' + jsonpickle.encode('Could not get a new job'))
                return event

            count += 1
    
    #extract job
    retry = 3
    count = 1
    while count <= retry:
        try:
            event['job_details'] = extract_job(event['raw_message'])
            break
        except:
            if count == retry:
              #delete from queue
              event['delete_message'] = delete_job(event)
              logger.error('## DELETE_FROM_SQS ERROR\r' + jsonpickle.encode(event['delete_message']))
              job_details = {
                    "job_id": "null",
                    "commands": "null",
                    "queue": "null",
                }

              event['Input']['LeaveRunning'] = 'True'
              event['job_details'] = job_details
              logger.error('## EXTRACT_JOB_ERROR\r' + jsonpickle.encode('Could not extract job details'))
              return event
            count += 1
    
    #start job
    retry = 3
    count = 1
    while count <= retry:
        try:
            event['DynamoDBResponse'] = grid_start_job(event)
            break
        except:
            time.sleep(1)
            logger.error('## START_JOB\r' + jsonpickle.encode('Failed to start job (write to dynamo async table)'))
            if count == retry:
                return event
            count += 1

    #delete job
    retry = 3
    count = 1
    while count <= retry:
        try:
            event['delete_message'] = delete_job(event)
            break
        except:
            time.sleep(1)
            logger.error('## DELETE_JOB\r' + jsonpickle.encode('Could not delete job'))
            if count == retry:
                raise ValueError('Could not delete job from SQS')
            count += 1
    
    return event
