import json
import os
import boto3
from .schema import ClustersSchema

stack_name = os.getenv("CYCLONE_STACKNAME", "cyclone")


class ClustersAWS(object):
    def __init__(self):
        self.region = "us-east-1"

    def get_clusters(self):
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        ddb_table = dynamodb.Table(f"{stack_name}_clusters_table")
        response = ddb_table.scan()
        data = response["Items"]
        while "LastEvaluatedKey" in response:
            response = ddb_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            data.extend(response["Items"])
        return [self.dump(cluster) for cluster in data]

    def dump(self, data):
        for key, value in data.items():
            if value == "True" or value == "False":
                data[key] = value.lower()
            if key == "instance_list":
                data[key] = json.loads(value)
            if key == "compute_resources_tags":
                data[key] = json.loads(value)
            if key == "iam_policies":
                data[key] = json.loads(value)
            if key == "bid_percentage":
                if data[key] == "" or data[key] == None:
                    data[key] = float(0)
        data = {k.lower(): v for k, v in data.items()}
        return ClustersSchema().dump(data)
