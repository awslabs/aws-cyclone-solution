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


LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()

def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    stack_name = os.environ.get("STACK_NAME")
    main_region = os.environ.get("MAIN_REGION")

    s3 = boto3.client('s3', region_name=main_region)
    
    def get_timestamp(elem):
        return datetime.fromisoformat(elem['time_stamp'])

    filterd_dict = {}
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
    bucket = stack_name + '-images-' + main_region
    for key, value in filterd_dict.items():
        sorted_values = sorted(value, key=get_timestamp, reverse=False)
        json_package = json.dumps({'data': sorted_values})
        queue, id = key.split('$$$$')
        key = 'logs/'+ queue + '/' + id + '/' + str(time.time()) + '.json'
        s3.put_object(Body=json_package, Bucket=bucket, Key=key)