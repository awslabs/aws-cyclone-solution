import os
import boto3
from .schema import JobsSchema

stack_name = os.getenv("CYCLONE_STACKNAME", "cyclone")


class JobsAWS(object):
    def __init__(self):
        self.region = ["us-east-1", "us-east-2", "us-west-1", "us-west-2"]

    def get_current_jobs(self):
        data = []
        for region in self.region:
            dynamodb = boto3.resource("dynamodb", region_name=region)
            ddb_table = dynamodb.Table(f"{stack_name}-core-{region}_table")
            response = ddb_table.scan()

            for item in response["Items"]:
                item["Region"] = region
            data.extend(response["Items"])

            while "LastEvaluatedKey" in response:
                response = ddb_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])

                for item in response["Items"]:
                    item["Region"] = region

                data.extend(response["Items"])

        return [self.dump(job) for job in data]

    def dump(self, data):
        for key, value in data.items():
            if value == "True" or value == "False":
                data[key] = value.lower()
        data = {k.lower(): v for k, v in data.items()}
        return JobsSchema().dump(data)
