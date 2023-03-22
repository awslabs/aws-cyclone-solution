import json
import boto3
from .schema import QueueSchema


class QueueAWS(object):
    def __init__(self, name):
        self.region = "us-east-1"
        self.name = name

    def get_queue(self):
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        ddb_table = dynamodb.Table(self.name)
        response = ddb_table.scan()
        data = response["Items"]
        while "LastEvaluatedKey" in response:
            response = ddb_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            data.extend(response["Items"])
        return [self.dump(region) for region in data]

    def dump(self, data):
        for key, value in data.items():
            if value == "True" or value == "False":
                data[key] = value.lower()
        data = {k.lower(): v for k, v in data.items()}
        return QueueSchema().dump(data)
