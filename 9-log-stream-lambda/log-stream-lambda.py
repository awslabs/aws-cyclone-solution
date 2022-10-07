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
import time
import requests
from requests_aws4auth import AWS4Auth
import uuid


LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

main_region = os.environ.get('MAIN_REGION')
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, main_region, service, session_token=credentials.token)

ssm = boto3.client('ssm', region_name=main_region)
stack_name = os.environ.get("STACK_NAME")

def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    stack_name = os.environ.get("STACK_NAME")
    main_region = os.environ.get("MAIN_REGION")

    dashboard_in_use = False
    try:
        domain_endpoint = ssm.get_parameter(Name=str(stack_name + '-es-endpoint'))
        domain_endpoint = domain_endpoint['Parameter']['Value']
        host = 'https://' +  domain_endpoint
        dashboard_in_use = True
        headers = { "Content-Type": "application/json" }
        es_index = 'logs'
        es_type = '_doc'
        url = host + '/_bulk'
        service = 'es'
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, main_region, service, session_token=credentials.token)
    except Exception as e:
        logger.info('## Dashboard not in use\r' + jsonpickle.encode(e))
        pass

    s3 = boto3.client('s3', region_name=main_region)
    
    def get_timestamp(elem):
        return datetime.fromisoformat(elem['time_stamp'])

    filterd_dict = {}
    string_payload = ''
    for record in event.get("Records"):
        # Kinesis data is base64 encoded so decode here
        message_str = base64.b64decode(record['kinesis']['data']).decode("utf-8")
        message = json.loads(message_str)
        logger.info('## Message\r' + jsonpickle.encode(message))

        for log_line in message:

            segment = log_line['jobQueue'] + "$$$$" + log_line['id']
            if not segment in filterd_dict:
                filterd_dict[segment] = []
                filterd_dict[segment].append(log_line)
            else:
                filterd_dict[segment].append(log_line)

            if dashboard_in_use:
                if log_line['log_type'] == 'STDOUT' or log_line['log_type'] == 'METRICS':
                    id = str(uuid.uuid4())
                    action = json.dumps({"index": {"_index": log_line['log_type'].lower(), "_id": id}}) + "\n"
                    line = json.dumps(log_line) + "\n"
                    string_payload += action
                    string_payload += line

    bucket = stack_name + '-images-' + main_region
    for key, value in filterd_dict.items():
        sorted_values = sorted(value, key=get_timestamp, reverse=False)
        json_package = json.dumps({'data': sorted_values})
        queue, id = key.split('$$$$')
        key = 'logs/'+ queue + '/' + id + '/' + str(time.time()) + '.json'
        s3.put_object(Body=json_package, Bucket=bucket, Key=key)
    
    try:
        r = requests.post(url, auth=awsauth, data=string_payload, headers=headers)
        logger.info('## ES response put action\r' + jsonpickle.encode(r.json()))
    except Exception as e:
        logger.error('## ES PUT FAILED\r' + jsonpickle.encode(e))
        pass