import json
import os
import boto3
from .schema import DefinitionsSchema

stack_name = os.getenv("CYCLONE_STACKNAME", "cyclone")


class DefinitionsAWS(object):
    def __init__(self, name=None):
        self.region = "us-east-1"
        self.name = name

    def get_definitions(self):
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        ddb_table = dynamodb.Table(f"{stack_name}_jobDefinitions_table")
        response = ddb_table.scan()
        data = response["Items"]
        while "LastEvaluatedKey" in response:
            response = ddb_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            data.extend(response["Items"])

        for queue in data:
            try:
                sqs_client = boto3.resource("sqs", region_name=self.region)
                sqs = sqs_client.get_queue_by_name(QueueName=queue["name"])
                queue["sqs_messages"] = sqs.attributes.get("ApproximateNumberOfMessages")
            except Exception as e:
                print(e)
        return [self.dump(definition) for definition in data]

    def purge_definition_queue(self):
        try:
            sqs_client = boto3.resource("sqs", region_name=self.region)
            sqs = sqs_client.get_queue_by_name(QueueName=self.name)
            sqs.purge()
            return "Ok"
        except Exception as e:
            return e

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
        return DefinitionsSchema().dump(data)
