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
import requests
from requests_aws4auth import AWS4Auth
from aws_xray_sdk.core import patch_all
import logging
import jsonpickle
import uuid
from datetime import datetime


LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

region = os.environ.get('REGION')
main_region = os.environ.get('MAIN_REGION')
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, main_region, service, session_token=credentials.token)

ssm = boto3.client('ssm', region_name=main_region)
stack_name = os.environ.get("STACK_NAME")

domain_endpoint = ssm.get_parameter(Name=str(stack_name + '-es-endpoint'))
domain_endpoint = domain_endpoint['Parameter']['Value']
host = 'https://' +  domain_endpoint

def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    headers = { "Content-Type": "application/json" }
    es_index = 'jobs'
    es_type = '_doc'
    url = host + '/' + es_index + '/' + es_type + '/'
    
    count = 0
    for record in event['Records']:

        if record.get('eventName') in ('INSERT', 'MODIFY'):

            id = record['dynamodb']['NewImage']['id']
            eslog = record['dynamodb']['NewImage']
            eslog['eventName'] = record['eventName']
            eslog['CurrentTime'] = datetime.now().isoformat()

            r = requests.put(url + str(id), auth=awsauth, json=eslog, headers=headers)
            logger.info('## ES response put action\r' + jsonpickle.encode(r.json()))
            count += 1

        elif 'REMOVE' in str(record['eventName']):

            id = record['dynamodb']['OldImage']['id']

            r = requests.delete(url + str(id), auth=awsauth)
            logger.info('## ES response delete action\r' + jsonpickle.encode(r.json()))
            count += 1
    
    es_index = 'job_history'
    url = host + '/' + es_index + '/' + es_type + '/'
    
    count = 0
    for record in event['Records']:

        if record.get('eventName') in ('INSERT', 'MODIFY'):

            id = str(uuid.uuid4())
            eslog = record['dynamodb']['NewImage']
            eslog['eventName'] = record['eventName']
            eslog['CurrentTime'] = datetime.now().isoformat()

            r = requests.put(url + str(id), auth=awsauth, json=eslog, headers=headers)
            logger.info('## ES response put action\r' + jsonpickle.encode(r.json()))
            count += 1
    logger.info('## Records processed\r' + jsonpickle.encode(count))
    return str(count) + ' records processed.'
