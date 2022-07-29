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

    ec2 = boto3.client('autoscaling', region_name=region)

    asg_list = []
    res = ec2.describe_auto_scaling_groups()
    for r in res['AutoScalingGroups']:
        print(r['AutoScalingGroupName'])
        for cluster in cluster_names:
            print('comapre  ' + r['AutoScalingGroupName'] + ' with ' + cluster)
            if cluster in r['AutoScalingGroupName']:
                print('FOUND: ' + r['AutoScalingGroupName'])
                asg_list.append(r['AutoScalingGroupName'])

    for asg in asg_list:

        response = ec2.set_desired_capacity(
            AutoScalingGroupName=asg,
            DesiredCapacity=0,
            HonorCooldown=False
        )

        while True:
            count = 0
            response = ec2.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg],
            )
            instance_list = []
            for instance in response['AutoScalingGroups'][0]['Instances']:
                if instance['LifecycleState'] == 'InService':
                    print('FOUND: ' + instance['InstanceId'] + ' in running mode')
                    count += 1
                    response = ec2.terminate_instance_in_auto_scaling_group(
                        InstanceId=instance['InstanceId'],
                        ShouldDecrementDesiredCapacity=True
                    )
            if count == 0:
                print('instance count is now 0 for ' + asg)
                break
        
        response = ec2.set_desired_capacity(
            AutoScalingGroupName=asg,
            DesiredCapacity=0,
            HonorCooldown=False
        )
