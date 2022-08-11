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
import time, argparse
from datetime import datetime
import json
from time import sleep
import json
import uuid
import subprocess
from subprocess import Popen, PIPE
from subprocess import check_output
import threading
from cpuinfo import get_cpu_info
import jsonpickle
import psutil
import os
import logging
import jsonpickle

#USE TO START ON WORKER VIA start.sh (also for local testing)
# python3 0-worker-agent/batch_processor.py --sf_arn arn:aws:states:xxxx:xxxxx:stateMachine:xxxx --async_table tableName --sqs_job_definition jobDefname --region region --main_region region --stack_name stackName

ENABLE_QLOG = os.getenv("ENABLE_QLOG", "True")

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

parser = argparse.ArgumentParser()
parser.add_argument('--sf_arn', nargs=1)
parser.add_argument('--async_table', nargs=1)
parser.add_argument('--sqs_job_definition', nargs=1)
parser.add_argument('--region', nargs=1)
parser.add_argument('--main_region', nargs=1)
parser.add_argument('--stack_name', nargs=1)
args = parser.parse_args()

sf_arn =  args.sf_arn[0]
table =  args.async_table[0]
jobDefinition =  args.sqs_job_definition[0]
region = args.region[0]
main_region = args.main_region[0]
stack_name = args.stack_name[0]

uuid = str(uuid.uuid4())

logger.info('## Initiated worker with params: \r' + jsonpickle.encode(args))

#dynamo_main = boto3.client('dynamodb', region_name=main_region)
dynamo = boto3.client('dynamodb', region_name=region)
sf = boto3.client('stepfunctions', region_name=region)
kinesis = boto3.client('kinesis', region_name=region)

def main():

    class heartbeat: 
        def __init__(self): 
            self._running = True
        
        def terminate(self): 
            self._running = False
            
        def run(self, TaskToken, region, stack_name, JobName, jobDefinition, JobQueue): 

            sf = boto3.client('stepfunctions', region_name=region)
            kinesis_2 = boto3.client('kinesis', region_name=region)

            while self._running:
                try:
                    sf.send_task_heartbeat(
                        taskToken=TaskToken
                    )
                    logger.info('## SENT HEARTBEAT TO SF: ' + jsonpickle.encode(datetime.now()))
                except Exception as e:
                    logger.error('## FAILED TO SEND HEARTBEAT TO SF: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
                    break

                try:
                    # Get metric data on cpu and mem usage
                    mem_data = psutil.virtual_memory()._asdict()
                    metric_data = {'cpu_count': psutil.cpu_count(), 'cpu_percent': psutil.cpu_percent(), 'mem_total_gb': mem_data['total']/1000000000, 'mem_used_gb':mem_data['used']/1000000000, 'mem_percent': mem_data['percent']}
                    package = [{'time_stamp': datetime.now().isoformat(), 'log_type': 'METRICS', 'id': JobName, 'jobDefinition': jobDefinition, 'jobQueue': JobQueue, 'data': metric_data}]
                    # Send to kinesis log stream in main region
                    kinesis_response = kinesis_2.put_record(
                        StreamName=stack_name + '_log_stream',
                        Data=bytes(json.dumps(package, default=str), 'utf-8'),
                        PartitionKey=jobDefinition
                    )
                    logger.info('## SENT METRIC PACKAGE: ' + jsonpickle.encode(datetime.now()))
                except Exception as e:
                    logger.error('## FAILED TO SEND METRICS PACKAGE: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
                    pass

                time.sleep(20)


    def log_push(stack_name, JobName, jobDefinition, JobQueue, buffer):
        if not ENABLE_QLOG == 'False' or ENABLE_QLOG == False:
            # Send to kinesis log stream in main region
            list_pack =[]
            time_stamp = datetime.now().isoformat()
            for line in buffer:
                list_pack.append({'time_stamp': time_stamp, 'log_type': 'STDOUT', 'id': JobName, 'jobDefinition': jobDefinition, 'jobQueue': JobQueue, 'data': line})
            try:
                kinesis_response = kinesis.put_record(
                    StreamName=stack_name + '_log_stream',
                    Data=bytes(json.dumps(list_pack, default=str), 'utf-8'),
                    PartitionKey=jobDefinition
                )
                logger.info('## SENT LOG PACKAGE: ' + jsonpickle.encode(datetime.now()))
            except Exception as e:
                logger.error('## FAILED TO SEND LOGS PACKAGE: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
                pass
    
    def do_work(cmd, callback, stack_name, JobName, jobDefinition, JobQueue):
        try:
            proc = subprocess.Popen([cmd],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.PIPE,
                                    universal_newlines = True,
                                    shell = True
                                    )
            buffer = []
            result = ''
            old_time = time.perf_counter()
            for line in iter(proc.stdout.readline, ''):
                buffer.append(line[:-1])
                result = result + line[:-1] + '\n'

                if len(buffer) > 1000 or time.perf_counter() - old_time >= 10:
                    callback(stack_name, JobName, jobDefinition, JobQueue, buffer)

                    buffer = []
                    old_time = time.perf_counter()
        
            if len(buffer) > 0:
                callback(stack_name, JobName, jobDefinition, JobQueue, buffer)
            while proc.poll() is None:
                pass
            if proc.returncode == 0:
                logger.info('## JOB SUCCESSFUL: ' + ' -- ' + jsonpickle.encode(datetime.now()))
                return result, 'Successful'
            else:
                result = 'FAILED\n' + proc.stderr.read()
                status = 'Failed'
                logger.info('## JOB FAILED: ' + jsonpickle.encode(result) + ' -- ' + jsonpickle.encode(datetime.now()))
                return result, status
        except Exception as e:
            logger.error('## JOB EXECUTION SUBPROCESS FAILED: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
            result = 'FAILED\n' + str(e)
            status = 'Failed'
            return result, status

    startTime = datetime.now()
    logger.info('## WORKER START TIME: ' + jsonpickle.encode(startTime))

    info = get_cpu_info()
    mem_info = psutil.virtual_memory()._asdict()

    #create dynamodb slot for command pickup
    response = dynamo.put_item(
        TableName=table,
        Item={
            'uuid': {
                'S': uuid},
            'command': {
                'S':'null'},
            'LeaveRunning': {
                "S":"True"},
            'Callback': {
                'S':'null'},
            'id': {
                'S':'null'},
            'Output': {
                'S':'null'},
            'CurrentTime': {
                'S': datetime.now().isoformat()},
            'Status': {
                'S':'null'},
            'jobDefinition': {
                'S':jobDefinition},
            'cpu_arch': {
                'S': info['arch'] or None},
            'cpu_count': {
                'S': str(info['count']) or None},
            'cpu_brand': {
                'S':info['brand_raw'] or None},
            'cpu_Hz': {
                'S':info['hz_advertised_friendly'] or None},
            'mem_total_gb': {
                'S':str(mem_info['total']/1000000000) or None},
            'mem_available_gb': {
                'S':str(mem_info['available']/1000000000) or None},
            'JobQueue': {
                'S':'null'}
            })

    #get queue name and launch SF with queue and uuid slot 


    input = {"sqs_name": jobDefinition,
                "uuid": uuid,
                "Callback": 'null',
                "LeaveRunning": 'True',
                "Output": 'null',
                "Status": 'null',
                "id": 'null',
                "table": table
            }

    #can include an x-ray id with line: traceHeader='string'
    response = sf.start_execution(
        stateMachineArn=sf_arn,
        name=uuid,
        input=json.dumps(input)
    )

    # start loop through jobs
    time.sleep(1)
    JobName = 'null'
    fail_safe = 0
    while True:
        #get record from dynamodb and confirm LeaveRunning is still True
        res = dynamo.get_item(
            TableName=table,
            Key={
                'uuid': {
                    'S': uuid}},       
            AttributesToGet=[
                'command',
                'LeaveRunning',
                'Callback',
                'id',
                'JobQueue'
            ])
        now = datetime.now()
        LeaveRunning = res['Item']['LeaveRunning']['S']

        if not LeaveRunning == 'True':
            logger.info('## LeaveRunning set to False by State Machine, exiting')
            response = sf.send_task_success(
                taskToken=res['Item']['Callback']['S'],
                output=json.dumps({"sqs_name": jobDefinition,
                                    "uuid": uuid,
                                    "Callback": 'null',
                                    "LeaveRunning": 'False',
                                    "Output": 'null',
                                    "Status": 'null',
                                    "id": 'null',
                                    "table": table
                                    })
            )
        
            break

        #see if job in dynamo is new or the previous one and if its not new wait 1 second then check again for 10 times until worker exits
        if JobName == res['Item']['id']['S']:
            fail_safe = fail_safe + 1
            logger.info('## No new Job in DynamoDB - Same id: ' + jsonpickle.encode(res['Item']['id']['S']))
            time.sleep(1)
            if fail_safe < 10:
                continue
            else:
                break
        
        #run a new job found
        logger.info('## FOUND NEW JOB IN DYNAMODB - JOB ID: ' + jsonpickle.encode(res['Item']))
        fail_safe = 0
        update1 = dynamo.update_item(
            TableName=table,
            Key={'uuid': {'S': uuid}},
            UpdateExpression="set #attr1 = :p, #attr3 = :q",
            ExpressionAttributeNames={'#attr1': 'Status', '#attr3': 'CurrentTime'},
            ExpressionAttributeValues={':p': {'S': 'Running'}, ':q': {'S': datetime.now().isoformat()}},
            ReturnValues="UPDATED_NEW"
            )
        
        now = datetime.now()
        logger.info('## RUNNING JOB: ' + jsonpickle.encode(now))

        JobName = res['Item']['id']['S']
        JobQueue = res['Item']['JobQueue']['S']
        command = res['Item']['command']['S']
        token = res['Item']['Callback']['S']
        
        try:
            c = heartbeat() 
            t = threading.Thread(target = c.run, kwargs={'TaskToken': token, 'region': region, 'stack_name': stack_name, 'JobName': JobName, 'jobDefinition': jobDefinition, 'JobQueue': JobQueue})
            t.start() 
        except Exception as e:
            logger.error('## HEARTBEAT THREAD FAILED: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))

        result, status = do_work(command, log_push, stack_name, JobName, jobDefinition, JobQueue)
        
        c.terminate() 

        try:
            out = result.splitlines()
            count = len(out)

            if count < 50:
                y = count *-1
            else:
                y = -50

            i = 0
            output = []
            for i in range(y, 0, 1):
                try:
                    output.append(out[i])
                except Exception:
                    output = 'Could Not Parse Output Lines'
        except Exception as e:
            logger.error('## FAILED TO PARSE OUTPUT LINES: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
            output = 'Could not parse output lines from job process'

        try: 
            update1 = dynamo.update_item(
                        TableName=table,
                        Key={'uuid': {'S': uuid}},
                        UpdateExpression="set #attr1 = :p, #attr2 = :r, #attr3 = :q",
                        ExpressionAttributeNames={'#attr1': 'Status', '#attr2': 'Output', '#attr3': 'CurrentTime'},
                        ExpressionAttributeValues={':p': {'S': str(status)}, ':r': {'S': str(output)}, ':q': {'S': datetime.now().isoformat()}},
                        ReturnValues="UPDATED_NEW"
                        )
        except Exception as e:
            logger.error('## COULD NOT UPDATE DYNAMODB WITH JOB STATUS AND RESULTS: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
            c.terminate()  
            break

        logger.info('## MARKED JOB AS FINISHED IN DYNAMODB' + ' -- ' + jsonpickle.encode(datetime.now()))
        
        try:
            response = sf.send_task_success(
                taskToken=token,
                output=json.dumps({"sqs_name": jobDefinition,
                                        "uuid": uuid,
                                        "Callback": 'null',
                                        "LeaveRunning": 'True',
                                        "Output": str(output),
                                        "Status": str(status),
                                        "id": str(JobName),
                                        "table": table
                                        })
            )
            logger.info('## NOTIFIED SF THAT JOB FINISHED' + ' -- ' + jsonpickle.encode(datetime.now()))
        except Exception as e:
            logger.error('## FAILED TO NOTIFY SF THAT JOB IS FINISHED: ' + jsonpickle.encode(e) + ' -- ' + jsonpickle.encode(datetime.now()))
            c.terminate()  
            break

        # Signal termination of heartbeat
        c.terminate()

    endTime = datetime.now()
    diffTime = endTime - startTime
    logger.info('## WORKER END TIME' + ' -- ' + jsonpickle.encode(endTime))
    logger.info('## WORKER RAN FOR' + ' -- ' + jsonpickle.encode(diffTime))

if __name__ == '__main__':
   main()