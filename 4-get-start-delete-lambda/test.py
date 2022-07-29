import json
import os
import boto3
import jsonpickle
import base64
import time

SQS = boto3.client("sqs")
dynamo = boto3.client('dynamodb')


def grid_start_job(event):
    print(json.dumps(event))
    response = dynamo.put_item(
        TableName=event['Input']['table'],
        Item={
            'uuid': {
                'S': event['Input']['uuid']},
            'command': {
                'S': str(event['job_details']['commands'])},
            'LeaveRunning': {
                "S": event['Input']['LeaveRunning']},
            'Callback': {
                'S': event['TaskToken']},
            'Status': {
                'S':'Starting'},
            'Output': {
                'S':'null'},
            'JobName': {
                'S': event['job_details']['job_id']}
            })
    print(json.dumps(response))
    return response

event = {
    "Input": {
        "sqs_name": "hyper-batch-2-JobStreamQueue5C6CB381-1GNX64PAY6KA3",
        "uuid": "a1372432-b7c3-44eb-9dc2-be56647cdbfe",
        "Callback": "null",
        "LeaveRunning": "True",
        "Output": "null",
        "Status": "null",
        "JobName": "null",
        "table": "hyper-batch-2-GlobalAsyncTable8E21928A-53A4EYOPGO0T"
    },
    "TaskToken": "AAAAKgAAAAIAAAAAAAAAAUlpeV07rGkhmj8sO0UY6AhzqGlhZDKZ2lsxRREFsX+okwU80vhsJ0MaoX6poh8mV1uZCSNFcD3QBDdcmSKVMD6UcAdrWeY1hZckoNOcjqoBGgmdEu7xR32ITMObSHkZ+XhoaXA3APPiKWtYXS50PQVpsEscQZdlo6rtlZPpu274xx5dp1YeAAh+TsLI/iyoB1mA7w+jW9CkLgum7lJQ/8Nw0sQpzUwEcbwnNVVazjpqE0n4C637STR8lnILK9xfnqv/UVzydquY+a4nzaEkHQUNz7elAkwWj0VKT2myBaAY/NAZpimHev4bjpODp/8O7ebgxOGto3SBgawvymzMlS+APRLNJPqq/M8ZbsdqpDs7hk2tygem9ZYin/ZbsMaAAyatB44y8w+o2njpId1gok+qKACqbQhMeqnw5Q+02Tu2gVSAldncfWUC31Nuhwr5J1+gU2FoaUFOWbhdcqmappwndhrU5qJ2iCFKKO+hbUF6JEP8VxY0gXuQVfw/Ye5hsMu15cZDvtkkcFZwnrGEqPWFnKD4nXxK4AescV13de9Ys0ST0kbOSIGj7PdSwNlk4A==",
    "raw_message": {
        "MessageId": "edb8a0b1-b416-4e36-b83b-2cfcfb292ed6",
        "ReceiptHandle": "AQEBPSI5srHeZ6ofLvJEh9809KN7rGCFDu0bYpcTKlyChtKNPRK+/26qN2GlWCfTD+0W6/CUK+aDfoTIcfrZN+lQy7N2e8pOLD9NTCs/khL9KfBLbL00HyoOMfAGjIXUWy96vb2WhT4KocSsCwQ9ytjwgCCpRzWj7FbXWvRP9X0XLJDJPRG+jaTZ7u/zJxDrWFdORJCycNnqYGnyjH00RueUIET3OHJYi1zjn7hhChZNHiMFuALfL8l0xHKqnXs/UNxChaEt3aTHNX+1j/CUfJQiBan+hwx3u1fWTvNWruk0lUJd8/iWoqpG6NSZHnP5vO8RTFaDxW4uAWp2idsvJeMnCJbYfotnHFD2Sm4toK94sLNfz+rXMCin4w4xGwByhnGB5yCJym5qryve91WrjAzBa2zUn+TuoIO/3xsSDXIeIhyUwSlHhB4w0n7YUBMwVlK6",
        "MD5OfBody": "787934b4577330f58f5ec6a16fcd6d35",
        "Body": "{\"jobName\": \"HelloWorld\", \"createdAt\": \"10-18-2020 10:28:15.715\", \"containerOverrides\": {\"environment\": [{\"name\": \"TABLE\", \"value\": \"hyper-batch-2-GlobalAsyncTable8E21928A-53A4EYOPGO0T\"}, {\"name\": \"JOB_DEFINITION\", \"value\": \"BatchJobDef0BB5F6F7-4a99e50f4d331e4:2\"}, {\"name\": \"SF_ARN\", \"value\": \"arn:aws:states:us-east-2:229287627589:stateMachine:hyper_batch\"}], \"memory\": 1024, \"command\": [\"python\", \"batch_processor.py\"]}, \"arrayProperties\": {\"size\": 2}, \"id\": \"bf88bae8-1763-412b-a9bd-775c4138361f\", \"region\": \"eu-west-1\", \"jobDefinition\": \"BatchJobDef0BB5F6F7-4a99e50f4d331e4:2\"}",
        "Attributes": {
            "SentTimestamp": "1603016900863"
        }
    },
    "job_details": {
        "job_id": "bf88bae8-1763-412b-a9bd-775c4138361f",
        "commands": [
            "python",
            "batch_processor.py"
        ]
    }
}

print(json.dumps(grid_start_job(event)))