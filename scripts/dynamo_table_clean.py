import boto3

def clean(region, table_name, att):

    table = boto3.resource('dynamodb', region_name=region).Table(table_name)

    scan = None

    with table.batch_writer() as batch:
        count = 0
        while scan is None or 'LastEvaluatedKey' in scan:
            if scan is not None and 'LastEvaluatedKey' in scan:
                scan = table.scan(
                    ProjectionExpression=att,
                    ExclusiveStartKey=scan['LastEvaluatedKey'],
                )
            else:
                scan = table.scan(ProjectionExpression=att)

            for item in scan['Items']:
                if count % 5000 == 0:
                    print(count)
                batch.delete_item(Key={att: item[att]})
                count = count + 1



clean('us-west-1','sample-queue-2', 'id')