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
from requests.auth import HTTPBasicAuth

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
    message = {
        "operation": "POST",
        "TableName": table,
        "payload": {"Item": item}
    }  
    header = {"x-api-key" : key}
    post = requests.post(url, data=json.dumps(message), headers=header)
    return post.json()

@click.group()
@click.pass_context
def queues(ctx):
    """Create, update & delete queues. Assign a cluster to use and region weights to control how jobs are distributed across regions for that queue. Not including a region or setting a weight of 0 will turn off a region for that queue. You can also select to have region weights automatically adjusted based on available spot capacity across different regions"""
    pass

@queues.command()
@click.pass_obj
@click.option('--name', required=False, default='', help='List queues')
def list_queues(obj, name):
    """List all queues currently configured for host."""
    
    # Execute the query on the transport
    results = scan(obj.url, obj.key, obj.name +'_queues_table')
    
    for queue in results:
        if queue['Status'] == 'ACTIVE':
            queue['Output_Log'] = 'SUCCESSFUL'
        else:
            queue['Output_Log'] = queue['Output_Log']
        click.echo('---------------------------------------')
        click.echo('                            ' + queue['name'])
        click.echo('---------------------------------------')
        for key in queue:
            click.echo('-------------------------')
            click.echo(key)
            click.echo(queue[key])
        click.echo('')

@queues.command()
@click.pass_obj
@click.option('-rw', '--region-distribution-weights', type=(str, int), multiple=True, default=None, required=False, help='IMPORTANT: Assign region weights for worker distribution. Repeat for multiple regions e.g "hyper queues add-queue -rw eu-west-1 3 -rw eu-central-1 1". Not including a region or using a weight of 0 means that region is not used. If you set automate region weights to True then weights are determined for you based on EC2 spot placement score.')
@click.option('--name', required=True, prompt='Queue name', help='Give queue a name')
@click.option('--compute-environment', required=True, prompt='EXACT MATCH Name of cluster to assign to this queue', help='Name of cluster to assign to this queue')
@click.option('--automate-region-weights', required=False, type=click.Choice(['True','False'], case_sensitive=False), default='True', show_default=True, prompt='Automatically adjust region weights based on available capacity', help='If set to true hyper-batch will use the EC2 Spot Placement Score API to set region weight distribution of jobs based on available capacity. The spot placement score looks at instance types configured for the cluster mapped to this queue as well as the max vCPU per region configured in cluster.')
def add_queue(obj, name, compute_environment, automate_region_weights, region_distribution_weights):
    """Add a queue to your environment, queues will span all enabled regions."""
    optimise_lowest_spot_cost_region = automate_region_weights
    if optimise_lowest_spot_cost_region == 'False':
        if not len(region_distribution_weights) > 0:
            num_regions = click.prompt('How many regions should be used for this queue?')
            click.echo('Enter regions using region codes, e.g us-east-1')
            weights_dict = {}
            for i in range(1, int(num_regions)+1, 1):
                r = click.prompt(f'Region code for region {i}')
                w = click.prompt(f'Weight (integer) for region {i}')
                weights_dict[r] = int(w)
            region_distribution_weights = json.dumps(weights_dict)
        else:
            weights_dict = {}
            for item in region_distribution_weights:
                r, w = item
                weights_dict[r] = w
            region_distribution_weights = json.dumps(weights_dict)
    else:
        results = scan(obj.url, obj.key, obj.name +'_regions_table')

        click.echo('Region weights will be automatically selected but you can control what regions are used for this queue')
        answer = click.prompt('Would you like to use all regions currently enabled?', type=click.Choice(['y','n'], case_sensitive=False), default='y', show_default=True)
        if answer == 'y':
            weights_dict = {}
            for region in results:
                if region['Status'] == 'ACTIVE':
                    click.echo(f'Region {region["name"]} is ACTIVE and will be used')
                    weights_dict[region['name']] = 'auto'
            region_distribution_weights = json.dumps(weights_dict)
        else:
            weights_dict = {}
            for region in results:
                if region['Status'] == 'ACTIVE':
                    answer = click.prompt(f'Would you like to use {region["name"]}?', type=click.Choice(['y','n'], case_sensitive=False), default='y', show_default=True)
                    if answer == 'y':
                        weights_dict[region['name']] = 'auto'
            region_distribution_weights = json.dumps(weights_dict)

    queue = {
        "name": name,
        "computeEnvironment": compute_environment,
        "optimise_lowest_spot_cost_region": optimise_lowest_spot_cost_region,
        "region_distribution_weights": region_distribution_weights,
        "Status": "Creating",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_queues_table', queue)

    click.echo('---------------------------------------')
    click.echo('                            ' + queue['name'])
    click.echo('---------------------------------------')
    for key in queue:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(queue[key])
    click.echo('')

@queues.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Queue name', help='Name of queue to update')
@click.option('--compute-environment', required=False, default=None, help='Name of cluster to assign to this queue')
@click.option('--automate-region-weights', required=False, type=click.Choice(['True','False'], case_sensitive=False), default='True', show_default=True, prompt='Automatically adjust region weights based on available capacity', help='If set to true hyper-batch will use the EC2 Spot Placement Score API to set region weight distribution of jobs based on available capacity. The spot placement score looks at instance types configured for the cluster mapped to this queue as well as the max vCPU per region configured in cluster.')
@click.option('-rw', '--region-distribution-weights', type=(str, int), multiple=True, required=False, help='IMPORTANT: Assign region weights for worker distribution. Repeat for multiple regions e.g "hyper queues add-queue -rw eu-west-1 3 -rw eu-central-1 1". Not including a region or using a weight of 0 means that region is not used. If you set automate region weights to True then weights are determined for you based on EC2 spot placement score.')
def update_queue(obj, name, compute_environment, automate_region_weights, region_distribution_weights):
    """Update specific configurations for an existing queue by specifying name of queue and config(s) to change with new values"""
    update = click.prompt('Would you like to update the region distribution weights?', type=click.Choice(['y','n'], case_sensitive=False), default='y', show_default=True)
    optimise_lowest_spot_cost_region = automate_region_weights
    if update == 'y':
        if optimise_lowest_spot_cost_region == 'False':
            if not len(region_distribution_weights) > 0:
                num_regions = click.prompt('How many regions should be used for this queue?')
                click.echo('Enter regions using region codes, e.g us-east-1')
                weights_dict = {}
                for i in range(1, int(num_regions)+1, 1):
                    r = click.prompt(f'Region code for region {i}')
                    w = click.prompt(f'Weight (integer) for region {i}')
                    weights_dict[r] = int(w)
                region_distribution_weights = json.dumps(weights_dict)
            else:
                weights_dict = {}
                for item in region_distribution_weights:
                    r, w = item
                    weights_dict[r] = w
                region_distribution_weights = json.dumps(weights_dict)
        else:
            results = scan(obj.url, obj.key, obj.name +'_regions_table')

            click.echo('Region weights will be automatically selected but you can control what regions are used for this queue')
            answer = click.prompt('Would you like to use all regions currently enabled?', type=click.Choice(['y','n'], case_sensitive=False), default='y', show_default=True)
            if answer == 'y':
                weights_dict = {}
                for region in results:
                    if region['Status'] == 'ACTIVE':
                        click.echo(f'Region {region["name"]} is ACTIVE and will be used')
                        weights_dict[region['name']] = 'auto'
                region_distribution_weights = json.dumps(weights_dict)
            else:
                weights_dict = {}
                for region in results:
                    if region['Status'] == 'ACTIVE':
                        answer = click.prompt(f'Would you like to use {region["name"]}?', type=click.Choice(['y','n'], case_sensitive=False), default='y', show_default=True)
                        if answer == 'y':
                            weights_dict[region['name']] = 'auto'
                region_distribution_weights = json.dumps(weights_dict)
    else:
        region_distribution_weights = None

    params_old = get(obj.url, obj.key, obj.name +'_queues_table', name)

    if not compute_environment == None:
        params_old['compute_environment'] = compute_environment
    if not optimise_lowest_spot_cost_region == None:
        params_old['optimise_lowest_spot_cost_region'] = optimise_lowest_spot_cost_region
    if not region_distribution_weights == None:
        params_old['region_distribution_weights'] = region_distribution_weights
    params_old['Status'] ='Updating'
    params_old['Output_Log'] =''

    
    queue = params_old

    post(obj.url, obj.key, obj.name +'_queues_table', queue)

    click.echo('---------------------------------------')
    click.echo('                            ' + queue['name'])
    click.echo('---------------------------------------')
    for key in queue:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(queue[key])
    click.echo('')

@queues.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Name of queue to delete', help='Queue name to delete')
def delete_queue(obj, name):
    """Delete a queue. Specify the name as --name <name>"""    

    params_old = get(obj.url, obj.key, obj.name +'_queues_table', name)

    params_old['Status'] = 'Deleting'
    params_old['Output_Log'] =''

    queue = params_old

    post(obj.url, obj.key, obj.name +'_queues_table', queue)

    click.echo('---------------------------------------')
    click.echo('                            ' + queue['name'])
    click.echo('---------------------------------------')
    click.echo('-------------------------')
    click.echo('Status')
    click.echo(queue['Status'])
    click.echo('')



