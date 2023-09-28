import json
import boto3
from .schema import BatchComputeSchema


class BatchComputeAWS(object):
    def __init__(self, region="us-east-1", job_queue_name=None):
        self.region = region
        self.job_queue_name = job_queue_name

    def get_batch_compute(self):
        batch = boto3.client("batch", region_name=self.region)
        queue_resp = batch.describe_job_queues(jobQueues=[self.job_queue_name])
        compute_envs = []
        for compute_env in queue_resp["jobQueues"][0]["computeEnvironmentOrder"]:
            comp_name = compute_env["computeEnvironment"].split("compute-environment/")
            compute_envs.append(comp_name[1])
        data = []
        resp = batch.describe_compute_environments(computeEnvironments=compute_envs)
        data = resp["computeEnvironments"]
        while "nextToken" in resp:
            resp = batch.describe_compute_environments(
                computeEnvironments=self.compute_environment, nextToken=resp["nextToken"]
            )
            data.extend(resp["computeEnvironments"])
        return [self.dump(compute) for compute in data]

    def dump(self, data):
        return BatchComputeSchema().dump(data)
