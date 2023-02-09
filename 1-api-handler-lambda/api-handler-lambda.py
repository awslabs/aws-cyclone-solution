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

def respond(err, res=None, id=None):
    res['job_id'] = id
    if not err:
        logger.info('## Submitted\r' + jsonpickle.encode(res))
    elif err:
        logger.info('## Failed submit\r' + jsonpickle.encode(res))
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

def respond_2(err, res=None):
    try:
        res = replace_decimals(res)
    except Exception:
        pass
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
    
    body = json.loads(event['body'])
    operation = body['operation']

    if operation == 'GET_KEYS':
        try:
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(body['payload']['bucket'])
            keys = []
            for key in bucket.objects.filter(Prefix='logs/' + body['TableName'] + '/' + body['payload']['id'] +'/'):
                keys.append(key.key)
            return {
                'statusCode': '200',
                'body': json.dumps(keys),
                'headers': {
                    'Content-Type': 'application/json',
                },
            }
        except Exception as e:
            logger.error('## Get log keys operation failed\r' + jsonpickle.encode(e))
            return {
                'statusCode': '400',
                'body': json.dumps(e),
                'headers': {
                    'Content-Type': 'application/json',
                },
            }

    if operation == 'GET_LOG':
        try:
            s3 = boto3.resource('s3')
            obj = s3.Object(body['payload']['bucket'], body['payload']['key']).get()
            res = json.loads(obj["Body"].read())
            return {
                'statusCode': '200',
                'body': json.dumps(res),
                'headers': {
                    'Content-Type': 'application/json',
                },
            }
        except Exception as e:
            logger.error('## Get log operation failed\r' + jsonpickle.encode(e))
            return {
                'statusCode': '400',
                'body': json.dumps(e),
                'headers': {
                    'Content-Type': 'application/json',
                },
            }
        


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

        if len(body['Item']) == 1:

            body['Item'] = body['Item'][0]

            now = datetime.now().isoformat()
            body['Item']["id"] = str(uuid.uuid4())
            body['Item']["Status"] = 'Waiting'
            body['Item']["Output"] = ' '
            body['Item']["tCreated"] = now
            logger.info('## DATA\r' + jsonpickle.encode(body['Item']))

            if 'jobName' not in body['Item']:
                body['Item']['jobName'] = body['Item']["id"]
                
            payload = {"Item": body['Item']}
            return respond(None, operations[operation](dynamo, payload), body['Item']["id"])
        elif len(body['Item']) > 1:
            now = datetime.now().isoformat()
            array_id = str(uuid.uuid4())
            count = 0
            try:
                with dynamo.batch_writer() as writer:
                    for item in body['Item']:
                        item['id'] = array_id + '--' + str(count)
                        item["Status"] = 'Waiting'
                        item["Output"] = ' '
                        item["tCreated"] = now
                        logger.info('## DATA\r' + jsonpickle.encode(item))
        
                        if 'jobName' not in item:
                            item['jobName'] = array_id
                        payload = {"Item": item}
                        writer.put_item(Item=item)
                        count = count + 1
                logger.info("Loaded data into table %s.", dynamo.name)
                res = {}
                res['job_id'] = array_id + '--N'
                return {
                            'statusCode': '200',
                            'body': json.dumps(res),
                            'headers': {
                                'Content-Type': 'application/json',
                            },
                        }
            except Exception as e:
                logger.exception("Couldn't load data into table %s.", dynamo.name)
                return {
                        'statusCode': '400',
                        'body': json.dumps(e),
                        'headers': {
                            'Content-Type': 'application/json',
                        },
                    }
                    
    elif operation == 'DELETE' and 'job_name' in body['payload']['Key']:
        payload = {
                        "KeyConditionExpression": '#ec4d3=:jobName',
                        "ProjectionExpression": "#ec4d0, #ec4d3",
                        "ExpressionAttributeNames": {"#ec4d0":"id","#ec4d3":"jobName"},
                        'ExpressionAttributeValues':{":jobName":body['payload']['Key']['job_name']},
                        'IndexName':'index_jobName',
                    }
        scan = None

        with dynamo.batch_writer() as writer:
            count = 0
            while scan is None or 'LastEvaluatedKey' in scan:
                if scan is not None and 'LastEvaluatedKey' in scan:
                    payload['ExclusiveStartKey'] = scan['LastEvaluatedKey']
                    scan = operations['QUERY'](dynamo, payload)
                else:
                    scan = operations['QUERY'](dynamo, payload)

                for item in scan['Items']:
                    print(item)
                    writer.delete_item(Key={'id': item['id']})
        res = {}
        res['job_name'] = body['payload']['Key']['job_name']
        res['ResponseMetadata'] = {}
        res['ResponseMetadata']['HTTPStatusCode'] = 200
        return {
                            'statusCode': '200',
                            'body': json.dumps(res),
                            'headers': {
                                'Content-Type': 'application/json',
                            },
                        }
    elif operation == 'GET' or 'DELETE' or 'PUT' or 'LIST' or 'QUERY':
        return respond_2(None, operations[operation](dynamo, body['payload']))
    else:
        logger.error('## Unsupported method ' + jsonpickle.encode(operation))
        return respond(ValueError('Unsupported method "{}"'.format(operation)))