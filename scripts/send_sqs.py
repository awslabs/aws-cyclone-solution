from __future__ import print_function
import boto3
import json
import jsonpickle

sqs = boto3.resource('sqs')

#Job definition JSON that is sent to SQS job queue

region = 'eu-west-1'

for i in range(0, 10, 1): #The number of loops defines how many test jobs to send
    
    jobid = 'jobId_' + str(i)
    message = json.dumps(
                    {   "region": region,
                        "jobName": jobid,
                        "RetriesAvailable": 2,
                        "jobDefinition": "hyperBatchDefinition",
                        "commands": "sleep 1; echo hello",
                        "Status": "Waiting",
                        "Output": "null",
                        "containerOverrides": {
                            "command": ["python", "batch_processor.py"],
                            "environment": [{
                                "name": "TABLE",
                                "value": "hyper_async_table_v3"
                            },
                            {
                                "name": "JOB_DEFINITION",
                                "value": "hyperBatchDefinition"
                            },
                            {
                                "name": "REGION",
                                "value": region
                            },
                            {
                                "name": "SF_ARN",
                                "value": str('arn:aws:states:'+ region + ':229287627589:stateMachine:hyper_batch')
                            }
                        ],
                            "memory": 1024
                        },
                        }  
                )
    print(message)
    sqs_name = 'hyperBatchDefinition'
    # Send a new job to SQS
    queue = sqs.get_queue_by_name(QueueName=sqs_name)
    response = queue.send_message(MessageBody=jsonpickle.encode(message))
    print('StatusCode: ' + str(response['ResponseMetadata']['HTTPStatusCode']))