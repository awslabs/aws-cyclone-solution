import boto3
import json

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

all_regions = get_config("./hyper_batch/configuration/regions.json")
def clean(region, table_name, att):

    table = boto3.resource('dynamodb', region_name=region).Table(table_name)

    scan = None

    with table.batch_writer() as batch:
        count = 0
        while scan is None or 'LastEvaluatedKey' in scan:
            if scan is not None and 'LastEvaluatedKey' in scan:
                scan = table.scan(
                    ProjectionExpression='#c',
                    ExpressionAttributeNames={'#c': att},
                    ExclusiveStartKey=scan['LastEvaluatedKey'],
                )
            else:
                scan = table.scan(ProjectionExpression='#c', ExpressionAttributeNames={'#c': att},)

            for item in scan['Items']:
                if count % 5000 == 0:
                    print(count)
                batch.delete_item(Key={att: item[att]})
                count = count + 1


all_regions = all_regions['regions']
region_list = []
for item in all_regions:
    region_list.append(item['region'])

print('found config: ' + str(region_list))

settings = get_config("./hyper_batch/configuration/settings.json")
stack_name = settings['stack_settings']['stack_name']
account = settings['stack_settings']['account']

for region in region_list:
    table = stack_name + '-core-' + region + '_table'
    print('CLEANING: ' + table + ' IN REGION ' + region)
    clean(region, table, 'uuid')



