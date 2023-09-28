import boto3
import os
from .schema import RegionSchema

stack_name = os.getenv("CYCLONE_STACKNAME", "cyclone")


class RegionAWS(object):
    def __init__(self):
        self.region = "us-east-1"

    def get_regions(self):
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        ddb_table = dynamodb.Table(f"{stack_name}_regions_table")
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
        return RegionSchema().dump(data)
