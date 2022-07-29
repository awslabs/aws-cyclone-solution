import boto3
import concurrent.futures
import json

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

settings = get_config("./hyper_batch/configuration/settings.json")
stack_name = settings['stack_settings']['stack_name']
account = settings['stack_settings']['account']


all_regions = get_config("./hyper_batch/configuration/regions.json")
all_regions = all_regions['regions']
region_list = []
for item in all_regions:
    region_list.append(item['region'])

print('found config: ' + str(region_list))

for region in region_list:

    print('LOOKING IN REGION: ' + region)

    STATE_MACHINE_ARN = 'arn:aws:states:' + region + ':' + account + ':stateMachine:' + stack_name + '-SfM'
    print('LOOKING AT SF ARN: ' + STATE_MACHINE_ARN)
    CONCURRENCY = 10

    client = boto3.client('stepfunctions', region_name=region)

    def stop_job(execution):
        arn = execution['executionArn']
        client.stop_execution(
            executionArn=arn
        )

        print('Stopped', arn)

        return arn

    paginator = client.get_paginator('list_executions')

    response_iterator = paginator.paginate(
        stateMachineArn=STATE_MACHINE_ARN,
        statusFilter='RUNNING',
        PaginationConfig={
            'PageSize': 1000
        }
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        results = []
        for page in response_iterator:
            futures = [
                executor.submit(stop_job, job) for job in page['executions']
            ]
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
            
        print('Stopped a total of', len(results), 'jobs')