#  Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import click
from click.termui import prompt # https://pypi.org/project/click/
from subprocess import Popen, PIPE
from subprocess import check_output
import json
import requests


def get(url, key, table, name):
    message = json.dumps(
                        {
                            "operation": "GET",
                            "TableName": table,
                            "payload":{"Key": {"name": name}
                            }
                        }  
    )

    header = {"x-api-key" : key}
    post = requests.post(url, data=message, headers=header)

    j = post.json()
    return j['Item']

def scan(url, key, table):
    message = json.dumps(
                    {
                        "operation": "LIST",
                        "TableName": table,
                        "payload":{}
                    }
                    )
    header = {"x-api-key" : key}
    post = requests.post(url, data=message, headers=header)

    j = post.json()
    return j['Items']

def post(url, key, table, item):
    message = json.dumps({
        "operation": "POST",
        "TableName": table,
        "payload": {"Item": item}
    })  
    header = {"x-api-key" : key}
    post = requests.post(url, data=message, headers=header)
    return post.json()


@click.group()
@click.pass_context
def clusters(ctx):
    """Create, update & delete clusters then associate the cluster with a queue in queue configuration. Clusters automatically extend across all enabled regions. You can control region weights for job distribution in the queue settings."""
    pass

@clusters.command()
@click.pass_obj
@click.option('--name', required=False, default='', help='List clusters')
def list_clusters(obj, name):
    """List all clusters currently configured for host."""
    
    results = scan(obj.url, obj.key, obj.name +'_clusters_table')

    for cluster in results:
        if cluster['Status'] == 'ACTIVE':
            cluster['Output_Log'] = 'SUCCESSFUL'
        else:
            cluster['Output_Log'] = cluster['Output_Log']
        click.echo('---------------------------------------')
        click.echo('                            ' + cluster['name'])
        click.echo('---------------------------------------')
        for key in cluster:
            click.echo('-------------------------')
            click.echo(key)
            click.echo(cluster[key])
        click.echo('')

@clusters.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Cluster name', help='Give cluster a name')
@click.option('--instance-list', required=True, default=["optimal"], show_default=True, prompt='Instance types as list of strings e.g ["m5.large","c5.large"] ', help='Instance types to use as a string list e.g ["m5.large","c5.large"], default is ["optimal"]')
@click.option('--max-vCPUs', required=True, default='1000', show_default=True, prompt='Max vCPUs per region', help='Specify the maximum vCPUs per region, total max vCPUs will be regions enabled * max-vCPUs per region')
@click.option('--type', required=True, default='SPOT', show_default=True, prompt='Choose [SPOT/ONDEMAND]', type=click.Choice(['SPOT','ONDEMAND'], case_sensitive=False),  help='Choose EC2 pricing plan [SPOT/ONDEMAND]')
@click.option('--bid-percentage', required=False, default=None, help='For SPOT only - Bid percentage of on-demand cost')
@click.option('--allocation-strategy', required=False, default=None, type=click.Choice(['SPOT_CAPACITY_OPTIMIZED','BEST_FIT_PROGRESSIVE', 'BEST_FIT'], case_sensitive=False), help='Batch allocation strategy to use [BEST_FIT_PROGRESSIVE/BEST_FIT/SPOT_CAPACITY_OPTIMIZED')
@click.option('--iam-policies', required=False, default=[], prompt='OPTIONAL Add IAM policies to instance role as list of strings e.g ["custom_policy"]', help='Add additional IAM policies to instance role in your cluster (policies needed by hyper batch are automatically added)')
@click.option('--main-region-image-name', required=False, default='', prompt='OPTIONAL Specify image name that exists in your main region to use for cluster', help='OPTIONAL Specify Image name for an image that exists in your main region that you want to use for cluster. Cyclone will copy the image to any hub regions where it does not exist and use local versions')
def add_cluster(obj, name, instance_list, max_vcpus, type, bid_percentage, allocation_strategy, iam_policies, main_region_image_name):
    """Add a cluster to your environment, clusters will span all enabled regions."""
    instance_list = str(instance_list).replace("'", '"')
    iam_policies = str(iam_policies).replace("'", '"')

    if '[' in instance_list and ']' in instance_list:
        pass
    else:
        click.echo('Instance list must be a list of strings e.g ["m5.large","c5.large"]')
        return
    if '"' in instance_list:
        pass
    else:
        click.echo('Instance list must be a list of strings e.g ["m5.large","c5.large"]')
        return
    

    if type == 'SPOT':
        if bid_percentage == None:
            bid_percentage = click.prompt('Choose spot bid percentage', default='100', show_default=True)
        if allocation_strategy == None:
            allocation_strategy = click.prompt('Choose spot allocation strategy', show_default=True, default='SPOT_CAPACITY_OPTIMIZED', type=click.Choice(['SPOT_CAPACITY_OPTIMIZED','BEST_FIT_PROGRESSIVE', 'BEST_FIT'], case_sensitive=False))

    cluster = {
        "name": name,
        "instance_list": instance_list,
        "type": type,
        "allocation_strategy": allocation_strategy,
        "bid_percentage": bid_percentage,
        "max_vCPUs": max_vcpus,
        "iam_policies": iam_policies,
        "main_region_image_name": main_region_image_name,
        "Status": "Creating",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_clusters_table', cluster)
    
    click.echo('---------------------------------------')
    click.echo('                            ' + cluster['name'])
    click.echo('---------------------------------------')
    for key in cluster:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(cluster[key])
    click.echo('')

@clusters.command()
@click.pass_obj
@click.option('--name', required=True, help='Choose cluster to update')
@click.option('--instance-list', required=False, default=None, help='List instance types to use e.g "m5.xlarge c5.xlarge", you can also choose optimal')
@click.option('--max-vCPUs', required=False, default=None, help='Specify the maximum vCPUs per region, total max vCPUs will be regions enabled * max-vCPUs per region')
@click.option('--type', required=False, default=None, help='Pricing option of spot or on-demand [SPOT/ON-DEMAND] ')
@click.option('--bid-percentage', required=False, default=None, help='If import-vpc is True then specify the vpc-id to import')
@click.option('--allocation-strategy', required=False, default=None, help='If set to True a peering connection is automatically create between hub region vpc and main region vpc for network communication')
@click.option('--iam-policies', required=False, default=None, help='Add additional iam policies to instance role in your cluster e.g ["custom_policy"] (policies needed by hyper batch are automatically added)')
@click.option('--main-region-image-name', required=False, default=None, help='OPTIONAL Specify Image name for an image that exists in your main region that you want to use for cluster. Cyclone will copy the image to any hub regions where it does not exist and use local versions')
def update_cluster(obj, name, instance_list, max_vcpus, bid_percentage, type, allocation_strategy, iam_policies, main_region_image_name):
    """Update specific configurations for an existing cluster"""

    params_old = get(obj.url, obj.key, obj.name +'_clusters_table', name)

    if not instance_list == None:
        params_old['instance_list'] = instance_list
    if not type == None:
        params_old['type'] = type
    if not max_vcpus == None:
        params_old['max_vCPUs'] = max_vcpus
    if not allocation_strategy == None:
        params_old['allocation_strategy'] = allocation_strategy
    if not bid_percentage == None:
        params_old['bid_percentage'] = bid_percentage
    if not iam_policies == None:
        params_old['iam_policies'] = iam_policies
    if not main_region_image_name == None:
        params_old['main_region_image_name'] = main_region_image_name
    params_old['Status'] ='Updating'
    params_old['Output_Log'] =''

    cluster = params_old

    post(obj.url, obj.key, obj.name +'_clusters_table', cluster)
    
    click.echo('---------------------------------------')
    click.echo('                            ' + cluster['name'])
    click.echo('---------------------------------------')
    for key in cluster:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(cluster[key])
    click.echo('')

@clusters.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Name of cluster to delete', help='AWS cluster name to delete')
def delete_cluster(obj, name):
    """Delete a cluster. Specify the name as --name <cluster name>"""    

    params_old = get(obj.url, obj.key, obj.name +'_clusters_table', name)

    params_old['Status'] = 'Deleting'
    params_old['Output_Log'] =''

    cluster = params_old

    post(obj.url, obj.key, obj.name +'_clusters_table', cluster)

    click.echo('---------------------------------------')
    click.echo('                            ' + cluster['name'])
    click.echo('---------------------------------------')
    click.echo('-------------------------')
    click.echo('Status')
    click.echo(cluster['Status'])
    click.echo('')



