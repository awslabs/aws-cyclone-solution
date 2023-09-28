import json
import os
import boto3
from .schema import QueuesSchema

stack_name = os.getenv("CYCLONE_STACKNAME", "cyclone")


class QueuesAWS(object):
    def __init__(self):
        self.region = "us-east-1"

    def get_queues(self):
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        ddb_table = dynamodb.Table(f"{stack_name}_queues_table")
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
            if key == "region_distribution_weights":
                data[key] = json.loads(value)
        data = {k.lower(): v for k, v in data.items()}
        return QueuesSchema().dump(data)
