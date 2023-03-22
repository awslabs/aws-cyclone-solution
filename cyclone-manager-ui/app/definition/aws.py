import json
import os
import boto3
from .schema import DefinitionSchema


stack_name = os.getenv("CYCLONE_STACKNAME", "cyclone")


class DefinitionAWS(object):
    def __init__(self, name):
        self.region = "us-east-1"
        self.name = name

    def get_definition(self):
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        ddb_table = dynamodb.Table(f"{stack_name}_jobDefinitions_table")
        response = ddb_table.get_item(Key={"name": self.name})
        data = response["Item"]

        return self.dump(data)

    def dump(self, data):
        for key, value in data.items():
            if value == "True" or value == "False":
                data[key] = value.lower()
            if key == "iam_policies":
                data[key] = json.loads(value)
            if key == "environment":
                data[key] = json.loads(value)
            if key == "linux_parameters":
                if value == "":
                    value = "null"
                data[key] = json.loads(value)
            if key == "timeout_minutes":
                if value == "":
                    value = 0
                data[key] = value
            if key == "user":
                if value == "":
                    value = "null"
                data[key] = json.loads(value)
            if key == "cyclone_image_name":
                if value == "":
                    value = "null"
                data[key] = json.loads(value)
            if key == "gpu_count":
                if value == "":
                    value = 0
                data[key] = value
            if key == "log_options":
                data[key] = json.loads(value)
            if key == "ulimits":
                data[key] = json.loads(value)
        data = {k.lower(): v for k, v in data.items()}
        return DefinitionSchema().dump(data)
