import json
import boto3
from .schema import BatchJobSchema


class BatchJobAWS(object):
    def __init__(self, region="us-east-1", job_queue_name=None):
        self.region = region
        self.job_queue_name = job_queue_name
        self.job_status_list = ["SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING"]

    def get_batch_jobs(self):
        batch = boto3.client("batch", region_name=self.region)
        data = []
        for status in self.job_status_list:
            resp = batch.list_jobs(jobQueue=self.job_queue_name, jobStatus=status)
            data.extend(resp["jobSummaryList"])
            while "nextToken" in resp:
                resp = batch.list_jobs(jobQueue=self.job_queue_name, jobStatus=status, nextToken=resp["nextToken"])
                data.extend(resp["jobSummaryList"])
        return [self.dump(jobs) for jobs in data]

    def purge_batch_jobs(self):
        batch = boto3.client("batch", region_name=self.region)
        print(f"Killing all batch jobs for queue: {self.job_queue_name}")
        for status in self.job_status_list:
            resp = batch.list_jobs(jobQueue=self.job_queue_name, jobStatus=status)
            data = resp["jobSummaryList"]
            while "nextToken" in resp:
                resp = batch.list_jobs(jobQueue=self.job_queue_name, jobStatus=status, nextToken=resp["nextToken"])
                data.extend(resp["jobSummaryList"])
            for job in data:
                try:
                    if status == "SUBMITTED" or status == "PENDING" or status == "RUNNABLE":
                        print(f"Canceling {status} batch job: {job['jobId']}")
                        batch.cancel_job(jobId=job["jobId"], reason="red button stop operation")
                    elif status == "STARTING" or status == "RUNNING":
                        print(f"Terminating {status} batch job: {job['jobId']}")
                        batch.terminate_job(jobId=job["jobId"], reason="red button stop operation")
                except Exception as e:
                    print(e)

    def dump(self, data):
        return BatchJobSchema().dump(data)
