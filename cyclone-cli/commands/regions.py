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
import boto3
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

    auth = HTTPBasicAuth('apikey', key)
    post = requests.post(url, auth=auth, data=message)

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
    auth = HTTPBasicAuth('apikey', key)
    post = requests.post(url, auth=auth, data=message)

    j = post.json()
    return j['Items']

def post(url, key, table, item):
    message = {
        "operation": "POST",
        "TableName": table,
        "payload": {"Item": item}
    }  
    auth = HTTPBasicAuth('apikey', key)
    post = requests.post(url, auth=auth, data=json.dumps(message))
    return post.json()

@click.group()
@click.pass_context
def regions(ctx):
    """INITIALIZE MAIN REGION and Add/Update/Delete hub regions like any other resource. Select peer-with-main-region true if you want a hub and spoke network for shared resources in main region VPC. DON'T FORGET to initialize your main region first with init-main-region"""
    pass

def get_vpcs(ctx, param, value):
    if value is not None:
        ec2 = boto3.client('ec2', region_name=value)
        vpcs = ec2.describe_vpcs()
        click.echo('')
        click.echo('EXISTING VPCS IN THIS REGION')
        for vpc in vpcs['Vpcs']:
            click.echo('----------------------------')
            click.echo(vpc['VpcId'])
            click.echo(vpc['CidrBlock'])
            click.echo('Default: ' + str(vpc['IsDefault']))
        click.echo('----------------------------')
        click.echo('')
        return value
        
@regions.command()
@click.pass_obj
@click.option('--import-vpc', required=False, default=None, help='[True/False] if you want to import a vpc specify --vpc-id <id> otherwise --cidr <cidr> and one is created for you.')
@click.option('--cidr', required=False, default=None, help='If import-vpc is False specify cidr to create e.g 10.0.0.0/16')
@click.option('--vpc-id', required=False, default=None, help='If import-vpc is True then specify the vpc-id to import')
@click.option('--deploy-vpc-endpoints', required=False, type=click.Choice(['OFF', 'DATA_OPTIMISED','FOR_PRIVATE_VPC'], case_sensitive=False), help='Deploy VPC endpoints either for data transfer cost optimisation only (use DATA_OPTIMISED) or to use private subnets(use FOR_PRIVATE_VPC')
def init_main_region(obj, import_vpc, cidr, vpc_id, deploy_vpc_endpoints):
    """START HERE - Initialize the main region for a newly created host. This is required before you can start configuring other regions, clusters, queues etc. for the host. Default parameters will match the host parameters or optionally change them"""
    if import_vpc == None:
        click.confirm('Are you sure you want to use same vpc as host? (if not see init-main-region --help)', abort=True)
    if deploy_vpc_endpoints == None:
        deploy_vpc_endpoints = click.prompt('Choose VPC endpoint group to deploy', type=click.Choice(['OFF', 'DATA_OPTIMISED','FOR_PRIVATE_VPC'], case_sensitive=False), default='OFF')

    region = {
        "name": obj.region,
        "main_region": 'True',
        "import_vpc": import_vpc or obj.import_vpc,
        "cidr": cidr or obj.cidr,
        "vpc_id": vpc_id or obj.vpc_id,
        "peer_with_main_region": 'False',
        "deploy_vpc_endpoints": deploy_vpc_endpoints,
        "Status": "Creating",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_regions_table', region)

    click.echo('---------------------------------------')
    click.echo('                            ' + region['name'])
    click.echo('---------------------------------------')
    for key in region:
        if key == 'peer_with_main_region':
            continue
        if region['import_vpc'] == 'True' and key == 'cidr':
            continue
        if region['import_vpc'] == 'False' and key == 'vpc_id':
            continue
        click.echo('-------------------------')
        click.echo(key)
        click.echo(region[key])
    click.echo('')

@regions.command()
@click.pass_obj
@click.option('--name', required=False, default='', help='Filter for a specific region, e.g. eu-west-1')
def list_regions(obj, name):
    """List all regions currently configured for host."""

    results = scan(obj.url, obj.key, obj.name +'_regions_table')

    for region in results:
        if region['Status'] == 'ACTIVE':
            region['Output_Log'] = 'SUCCESSFUL'
        else:
            region['Output_Log'] = region['Output_Log']
        click.echo('---------------------------------------')
        click.echo('                            ' + region['name'])
        click.echo('---------------------------------------')
        for key in region:
            if region['import_vpc'] == 'True' and key == 'cidr':
                continue
            if region['import_vpc'] == 'False' and key == 'vpc_id':
                continue
            click.echo('-------------------------')
            click.echo(key)
            click.echo(region[key])
        click.echo('')


@regions.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Enter new region code as name, e.g. eu-west-1', callback=get_vpcs, help='AWS region to add, e.g. eu-west-1')
@click.option('--vpc', required=True, default='', prompt='If creating vpc specify cidr range to use or specify a vpc-id to import existing vpc (recommended) e.g 10.0.0.0/16 OR vpc-xxxx', help='Import or create a vpc to use by specifying either a cidr or vpc-id (e.g 10.0.0.0/16 OR vpc-xxxx)')
@click.option('--peer-with-main-region', required=True, type=click.Choice(['True','False'], case_sensitive=False), default='False', prompt='[True/False] Peering between hub region private subnets and main region private subnets', help='If set to True a peering connection is automatically create between hub region vpc and main region vpc for network communication. The main region vpc will need private subnets available for this to work.')
@click.option('--deploy-vpc-endpoints', required=True, type=click.Choice(['OFF', 'DATA_OPTIMISED','FOR_PRIVATE_VPC'], case_sensitive=False), default='OFF', prompt='OPTIONAL Choose VPC endpoint group to deploy', help='Deploy VPC endpoints either for data transfer cost optimisation only (use DATA_OPTIMISED) or to use private subnets(use FOR_PRIVATE_VPC')
def add_region(obj, name, vpc, peer_with_main_region, deploy_vpc_endpoints):
    """Add a hub region to your environment to increase scheduling performance and available capacity. Clusters will automatically extend across all enabled regions and by selecting peer to main region "True' you can ensure connectivity to NFS/SMB storage and license servers."""
    if 'vpc-' in vpc:
        import_vpc = 'True'
        vpc_id = vpc
        cidr='null'
        ec2 = boto3.client('ec2', region_name=name)
        vpcs = ec2.describe_vpcs()
        if not vpc in str(vpcs):
            click.echo('VpcId not found in this region')
            return 'VpcId not found in this region'
    else:
        import_vpc = 'False'
        vpc_id = 'null'
        cidr = vpc
        ec2 = boto3.client('ec2', region_name=name)
        vpcs = ec2.describe_vpcs()
        if vpc in str(vpcs):
            click.echo('CIDR already exists in this region, choose another CIDR')
            return 'CIDR already exists in this region, choose another CIDR'
    
    region = {
        "name": name,
        "main_region": 'False',
        "import_vpc": import_vpc,
        "cidr": cidr,
        "vpc_id": vpc_id,
        "peer_with_main_region": peer_with_main_region,
        "deploy_vpc_endpoints": deploy_vpc_endpoints,
        "Status": "Creating",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_regions_table', region)

    click.echo('---------------------------------------')
    click.echo('                            ' + region['name'])
    click.echo('---------------------------------------')
    for key in region:
        if region['import_vpc'] == 'True' and key == 'cidr':
            continue
        if region['import_vpc'] == 'False' and key == 'vpc_id':
            continue
        click.echo('-------------------------')
        click.echo(key)
        click.echo(region[key])
    click.echo('')

@regions.command()
@click.pass_obj
@click.option('--name', required=True, help='AWS region to update, e.g. eu-west-1')
@click.option('--import-vpc', required=False, help='[True/False] if you want to import a vpc specify --vpc-id <id> otherwise --cidr <cidr> and one is created for you.')
@click.option('--cidr', required=False, help='If import-vpc is False specify cidr to create e.g 10.0.0.0/16')
@click.option('--vpc-id', required=False, help='If import-vpc is True then specify the vpc-id to import')
@click.option('--peer-with-main-region', required=False, help='If set to True a peering connection is automatically create between hub region vpc and main region vpc for network communication')
@click.option('--deploy-vpc-endpoints', required=False, type=click.Choice(['OFF', 'DATA_OPTIMISED','FOR_PRIVATE_VPC'], case_sensitive=False), help='Deploy VPC endpoints either for data transfer cost optimisation only (use DATA_OPTIMISED) or to use private subnets(use FOR_PRIVATE_VPC')
def update_region(obj, name, import_vpc, cidr, vpc_id, peer_with_main_region, deploy_vpc_endpoints):
    """Update specific configurations for an existing hub region"""
    
    params_old = get(obj.url, obj.key, obj.name +'_regions_table', name)
    
    if not import_vpc == None:
        params_old['import_vpc'] =import_vpc
    if not cidr == None:
        params_old['cidr'] = cidr
    if not vpc_id == None:
        params_old['vpc_id'] = vpc_id
    if not peer_with_main_region == None:
        params_old['peer_with_main_region'] = peer_with_main_region
    if not deploy_vpc_endpoints == None:
        params_old['deploy_vpc_endpoints'] = deploy_vpc_endpoints
    params_old['Status'] ='Updating'
    params_old['Output_Log'] =''


    region = params_old

    post(obj.url, obj.key, obj.name +'_regions_table', region)

    click.echo('---------------------------------------')
    click.echo('                            ' + region['name'])
    click.echo('---------------------------------------')
    for key in region:
        if region['import_vpc'] == 'True' and key == 'cidr':
            continue
        if region['import_vpc'] == 'False' and key == 'vpc_id':
            continue
        click.echo('-------------------------')
        click.echo(key)
        click.echo(region[key])
    click.echo('')

@regions.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Region to delete', help='AWS region to delete, e.g. eu-west-1')
def delete_region(obj, name):
    """Delete a hub region. Specify the region as --name <region>"""    

    params_old = get(obj.url, obj.key, obj.name +'_regions_table', name)

    params_old['Status'] = 'Deleting'
    params_old['Output_Log'] =''

    region = params_old

    post(obj.url, obj.key, obj.name +'_regions_table', region)

    click.echo('---------------------------------------')
    click.echo('                            ' + region['name'])
    click.echo('---------------------------------------')
    click.echo('-------------------------')
    click.echo('Status')
    click.echo(region['Status'])
    click.echo('')



