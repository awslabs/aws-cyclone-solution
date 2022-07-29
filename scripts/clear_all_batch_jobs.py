import boto3
import json

def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

all_regions = get_config("./hyper_batch/configuration/regions.json")
all_regions = all_regions['regions']
region_list = []
for item in all_regions:
    region_list.append(item['region'])

print('found config: ' + str(region_list))

cluster_config = get_config("./hyper_batch/configuration/clusters.json")
cluster_config = cluster_config['clusters']

cluster_names = []
for item in cluster_config:
    cluster_names.append(item['clusterName'].replace('-',''))

print('found config clusters (removed dash): ' + str(cluster_names))

for region in region_list:

    print('LOOKING IN REGION: ' + region)

    batch = boto3.client('batch', region_name=region)
    status_list_1 = ['SUBMITTED','PENDING','RUNNABLE','STARTING','RUNNING']
    status_list_2 = ['RUNNING','STARTING']

    queue_list = []
    res = batch.describe_job_queues()
    for r in res['jobQueues']:
        print(r['jobQueueName'])
        for cluster in cluster_names:
            print('comapre  ' + r['jobQueueName'] + ' with ' + cluster)
            if cluster in r['jobQueueName']:
                print('FOUND: ' + r['jobQueueName'])
                queue_list.append(r['jobQueueName'])

    for queue in queue_list:

        for status in status_list_1:
            response = batch.list_jobs(
                jobQueue=queue,
                jobStatus=status,
            )
            for item in response['jobSummaryList']:
                job_id = item['jobId']
                print('CANCEL: ' + item['jobId'])
                response = batch.cancel_job(
                    jobId=item['jobId'],
                    reason='red button stop operation'
                )
                print(response)
                try:
                    print('TERMINATE: ' + item['jobId'])
                    response = batch.terminate_job(
                        jobId=item['jobId'],
                        reason='red button stop operation'
                    )
                    print('Terminated ' + item['jobId'] + ' in state ' + status)
                except Exception:
                    #terminate calls can get throttled or may not find the job in which case the script should continue terminating other jobs, the script is later re run several times to ensure everything is terminated
                    pass
        
        for status in status_list_2:
            response = batch.list_jobs(
                jobQueue=queue,
                jobStatus=status,
            )
            for item in response['jobSummaryList']:
                job_id = item['jobId']
                print('TERMINATE: ' + item['jobId'])
                response = batch.terminate_job(
                    jobId=item['jobId'],
                    reason='red button stop operation'
                )
                print('Terminated ' + item['jobId'] + ' in state ' + status)