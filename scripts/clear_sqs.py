import boto3
import json

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

all_regions = get_config("./hyper_batch/configuration/regions.json")
all_regions = all_regions['regions']

for item in all_regions:
    if item['main_region'] == 'True':
        region = item['region']

print('found config main region: ' + region)

job_definitions_config = get_config("./hyper_batch/configuration/job_definitions.json")
job_definitions = job_definitions_config['jobDefinitions']

def_names = []
for item in job_definitions:
    def_names.append(item['jobDefinitionName'])

print('found config job definitions: ' + str(def_names))

sqs = boto3.client('sqs', region_name=region)

for queue in def_names:

    url_res = sqs.get_queue_url(
        QueueName=queue,
    )

    response = sqs.purge_queue(
        QueueUrl=url_res['QueueUrl']
    )

    print('PURGED:' + queue)
