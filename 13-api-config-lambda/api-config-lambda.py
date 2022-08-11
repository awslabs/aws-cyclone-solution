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
from boto3.dynamodb.conditions import Key
from aws_xray_sdk.core import patch_all
import logging
import jsonpickle
import uuid
from datetime import datetime
import decimal

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()


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

def respond(err, res=None):
    res = replace_decimals(res)
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

def lambda_handler(event, context):
    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))
    print(event)
    
    body = json.loads(event['body'])
    operation = body['operation']


    if 'TableName' not in body:
        logger.error('## Queue not found\r' + jsonpickle.encode(body['TableName']))
        return respond(ValueError('Did not find TableName (jobQueue name)'))
    else:
        dynamo = boto3.resource('dynamodb').Table(body['TableName'])

    operations = {
        'DELETE': lambda dynamo, x: dynamo.delete_item(**x),
        'GET': lambda dynamo, x: dynamo.get_item(**x),
        'POST': lambda dynamo, x: dynamo.put_item(**x),
        'PUT': lambda dynamo, x: dynamo.update_item(**x),
        'LIST': lambda dynamo, x: dynamo.scan(**x),
        'QUERY': lambda dynamo, x: dynamo.query(**x)
    }

    if operation == 'POST':
        try:
            ecs = boto3.client('ecs')
            stack_name = os.getenv("STACK_NAME", 'null')
            cluster = stack_name+'-orch-cluster'
            taskdef = stack_name+'-Taskdef'
            cappro = stack_name+'-CapPro'

            ecs.run_task(
                capacityProviderStrategy=[
                    {
                        'capacityProvider': cappro,
                        'weight': 1,
                        'base': 0
                    },
                ],
                cluster=cluster,
                count=1,
                taskDefinition=taskdef
            )
        except Exception as e:
            return respond(ValueError('Could not run ECS build task: "{}"'.format(str(e))))
            

    if operation == 'GET' or 'POST' or 'PUT' or 'LIST' or 'QUERY':
        if operation == 'POST':
            body['payload'] = json.loads(json.dumps(body['payload']), parse_float=decimal.Decimal)
        return respond(None, operations[operation](dynamo, body['payload']))
    else:
        logger.error('## Unsupported method ' + jsonpickle.encode(operation))
        return respond(ValueError('Unsupported method "{}"'.format(operation)))