import json
import boto3
from .schema import BatchQueueSchema


class BatchQueueAWS(object):
    def __init__(self, region="us-east-1"):
        self.region = region

    def get_batch_queues(self):
        batch = boto3.client("batch", region_name=self.region)
        resp = batch.describe_job_queues()
        data = resp["jobQueues"]
        while "nextToken" in resp:
            resp = batch.describe_job_queues(nextToken=resp["nextToken"])
            data.extend(resp["jobQueues"])
        # filter for cyclone queues
        data = [item for item in data if "cyclone" in item["jobQueueName"]]
        return [self.dump(queues) for queues in data]

    def dump(self, data):
        return BatchQueueSchema().dump(data)
