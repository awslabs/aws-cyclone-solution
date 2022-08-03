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
import json
import os
import subprocess
from subprocess import Popen, PIPE
from subprocess import check_output
import re
import json
import secrets

def get_account():
    try:
        account = boto3.client('sts').get_caller_identity().get('Account')
        return account
    except Exception:
        return 'no aws creds found'

def get_region():
    try:
        region = boto3.client('sts').meta.region_name
        return region
    except Exception:
        return 'no aws creds found'


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

def do_work(command_list):
    try:
        output = []
        for command in command_list:
            print(' ')
            print('------------------------------------------------------------')
            print('Running: ' + command)
            print('------------------------------------------------------------')

            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            if result.returncode == 0:
                status = 'ACTIVE'

                for line in result.stdout.splitlines():
                    print(line)
                    output.append(line)

                for line in result.stderr.splitlines():
                    print(line)
                    output.append(line)
            else:
                status = 'FAILED'

                for line in result.stdout.splitlines():
                    print(line)
                    output.append(line)

                for line in result.stderr.splitlines():
                    print(line)
                    output.append(line)
                return output, status
        return output, status
    except subprocess.CalledProcessError as e:
        output = 'FAILED ' + str(e)
        status = 'FAILED'
        return output, status

def create_front_end(stack_name, region, account, enable_dashboard, import_vpc, vpc_id, cidr):
    command0 = 'cdk bootstrap aws://{}/{} --force'.format(account, region)
    command2 = 'cdk deploy {}-front-end-{}'.format(stack_name, region)
    command = [command0, command2]
    result, status = do_work(command)

    return result, status

def get_vpcs(ctx, param, value):
    if value is not None:
        ec2 = boto3.client('ec2', region_name=value)
        vpcs = ec2.describe_vpcs()
        click.echo('')
        click.echo('EXISTING VPCS IN THIS REGION')
        for vpc in vpcs['Vpcs']:
            click.echo('----------------------------')
            if vpc['IsDefault'] == True:
                click.echo('DEFAULT')
            click.echo(vpc['VpcId'])
            click.echo(vpc['CidrBlock'])
            click.echo('Default: ' + str(vpc['IsDefault']))
        click.echo('----------------------------')
        click.echo('')
        return value

@click.group()
@click.pass_context
def hosts(ctx):
    """START HERE: Create a new host and start configuring your clusters, queues, task definitions & images. This section of the Hyper CLI requires IAM credentials for initial deployment of hosts while the other sections of the CLI use API and API credentials. You can have multiple hosts deployed and switch between them with select-host and relevent API URL & credentials will be loaded into CLI from local storage.  List existing hosts with list-hosts."""
    pass

@hosts.command()
@click.pass_context
@click.option('--name', required=True, prompt='Give your host a name (CF stack name compliant)',  help='Give your new host a name, this becomes the stack name and all resources are associated with this')
@click.option('--account', required=True, default=get_account(), prompt='Account to deploy host to', help='AWS account to deploy host to, e.g. 123xxxx456')
@click.option('--region', required=True, default=get_region(), prompt='Region to deploy host to', callback=get_vpcs, help='AWS region to deploy host to, e.g. eu-west-1')
@click.option('--vpc', required=True, default='', prompt='If creating vpc specify cidr range to use or specify a vpc-id to import existing vpc (recommended) e.g 10.0.0.0/16 OR vpc-xxxx', help='Import or create a vpc to use by specifying either a cidr or vpc-id (e.g 10.0.0.0/16 OR vpc-xxxx)')
@click.option('--enable-dashboard', required=True, type=click.Choice(['True','False'], case_sensitive=False), prompt='[True/False] Deploy Kibana+ElasticSearch with worker & job log ingestion', help='[True/False] Deploy Kibana + ElasticSearch Cluster and data ingestion Lambdas that push all job and worker state changes to cluster. This will create a continuos cost for having solution deployed outside usage')
@click.option('--auto-init-main',required=False, default='True', type=click.Choice(['True','False'], case_sensitive=False), help='Default [True] - Automatically initialize main region when host is created, put False only if you want to use a different vpc in main region and configure this after host creation with init-main-region command')
def create_host(ctx, name, account, region, enable_dashboard, vpc, auto_init_main):
    """Create a new host and start configuring your clusters, queues, task definitions & images. After that you can start running jobs with qsub command"""

    if 'vpc-' in vpc:
        import_vpc = 'True'
        vpc_id = vpc
        cidr='null'
        ec2 = boto3.client('ec2', region_name=region)
        vpcs = ec2.describe_vpcs()
        if not vpc in str(vpcs):
            click.echo('VpcId not found in this region')
            return 'VpcId not found in this region'
        
        subnets = ec2.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        vpc_id
                    ]
                }
            ])
        click.echo(' ')
        click.echo(f'SUBNETS AVAILABLE IN {vpc_id}')
        for subnet in subnets['Subnets']:
            subnet_id = subnet['SubnetId']
            map_ip = subnet['MapPublicIpOnLaunch']
            click.echo('----------------------------')
            click.echo(f'SUBNETS_ID: {subnet_id}')
            click.echo(f'      MAP_PUBLIC_IP_ON_LAUNCH: {map_ip}')
            route_tables = ec2.describe_route_tables(
                Filters=[
                    {
                        'Name': 'association.subnet-id',
                        'Values': [
                            subnet_id
                        ]
                    }
                ])
            if len(route_tables['RouteTables']) > 0:
         
                for routeTable in route_tables['RouteTables']:
                    for route in routeTable['Routes']:
                        route.pop('Origin')
                        click.echo(f'      ROUTE: {route}')



            else:
                route_tables = ec2.describe_route_tables(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [
                            vpc_id,
                        ]
                    },
                    {
                        'Name': 'association.main',
                        'Values': [
                            'true'
                        ]
                    }
                ])

                for routeTable in route_tables['RouteTables']:
                    for route in routeTable['Routes']:
                        route.pop('Origin')
                        click.echo(f'      ROUTE: {route}')
        click.echo('----------------------------')
        click.echo(' ')
        subnet_to_use = click.prompt('Please enter a subnet_id to use that has internet access')
                                       
    else:
        import_vpc = 'False'
        vpc_id = 'null'
        cidr = vpc
    
    #not able to create new vpc with cloudformation, only with cdk deployment option
    if import_vpc == 'False':
        click.echo('CREATE HOST VPC IS ONLY SUPPORTED when using "hyper hosts create-host-with-cdk", if you do not have cdk installed you need to import a vpc. See README for cdk installation instructions if you want to use create-host-with-cdk. PLEASE NOTE: This vpc is only hosting your control plane, you can still create vpcs that are used for your clusters with "hyper regions init-main-region" (see options for this command with --help) & "hyper regions add-region"')
        return

    click.echo('')
    res = subprocess.run('docker info', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if not res.returncode == 0:
        click.echo('Docker agent not running, EXITING deployment')
        return 'Docker agent not running, EXITING deployment'

    click.echo(' ')
    click.echo('stack_name=' + name + ' / ' + 'account=' + account + ' / ' + 'region=' + region + ' / ' 'enable_dashboard=' + enable_dashboard+ ' / ' + 'import_vpc=' + import_vpc + ' / ' + 'cidr=' + cidr + ' / ' + 'vpc_id=' + vpc_id)
    click.echo('Deploying new host.....')
    click.echo('This takes 5 min or more depending on internet speed...')

    if import_vpc == 'True':
        current_name = 'place-holder'
        current_account = '123456789876'
        current_region = 'eu-west-1'
        current_vpc_id = 'vpc-1234xxx1234'
        current_enable_dashboard = 'enable_dashboard_true_or_false'
        current_repo = 'placeholder_repo'
        current_subnet = 'placeholder_subnet'
        current_api_key = 'placeholder_api_key'
        
        base_temp = 'template.json'
        repo = name + '-deploy'

        j = get_config(base_temp)
        resources = j['Resources']
        for res in resources:
            try:
                del j['Resources'][res]['Metadata']
            except Exception:
                pass

        s = json.dumps(j)

        resources = j['Resources']

        for res in resources:
            new_res=res
            if current_name in new_res:
                new_res = new_res.replace(current_name, name)
            elif re.sub('[^A-Za-z0-9]+', '', current_name) in new_res:
                new_res = new_res.replace(re.sub('[^A-Za-z0-9]+', '', current_name), re.sub('[^A-Za-z0-9]+', '', name))
            else:
                new_res = re.sub('[^A-Za-z0-9]+', '', name) + new_res
            
            s = s.replace(res, new_res)

        s = s.replace(current_vpc_id, vpc_id)
        s = s.replace(current_subnet, subnet_to_use)
        s = s.replace(current_region, region)
        s = s.replace(current_account, account)
        s = s.replace(current_name, name)
        s = s.replace(current_repo, repo)
        s = s.replace(current_api_key, secrets.token_urlsafe(25))
        s = s.replace(current_enable_dashboard, enable_dashboard)
        s = s.replace(re.sub('[^A-Za-z0-9]+', '', current_name), re.sub('[^A-Za-z0-9]+', '', name))

        s = json.loads(s)

        with open("package-template.json", 'w') as outfile:
                        json.dump(s, outfile, indent=4,sort_keys=True)
        
        command0 = 'aws s3 mb s3://{}-deployment --region {}'.format(name, region)
        output, status = do_work([command0])
        if status == 'FAILED':
            if 'BucketAlreadyOwnedByYou' in str(output):
                click.echo('Found existing bucket and proceeding: ' + name + '-deployment')
            else:
                click.echo('Failed to create new bucket: ' + name + '-deployment')
                return
        
        #run cloudformation package to push assets to s3
        command1 = 'aws cloudformation package --template-file package-template.json --s3-bucket {}-deployment --output-template-file clean-template.json --use-json --region {}'.format(name, region)
        output, status = do_work([command1])
        if status == 'FAILED':
            click.echo('Failed to package cloudformation and push assets to S3 bucket: ' + name + '-deployment')
            return
        
        command2 = 'aws ecr create-repository --repository-name {}-deploy --image-scanning-configuration scanOnPush=true --region {}'.format(name, region)
        output, status = do_work([command2])
        if status == 'FAILED':
            if 'already exists' in str(output):
                click.echo('Found existing repo with this name and proceeding: ' + name + '-deploy')
            else:
                click.echo('Failed to create new repo: ' + name + '-deploy')
                return
        
        command3 = 'docker build -t {}.dkr.ecr.{}.amazonaws.com/{}-deploy:orchestrator .'.format(account, region, name)
        output, status = do_work([command3])
        if status == 'FAILED':
            click.echo('Failed to build image: ' + name + '-deploy')
            return

        click.echo('')
        click.echo('Pushing 4Gb Image to ECR, can take some time depending on internet')
        #build and push image to ecr for orchestrator service
        command = 'bash push_to_ecr.sh {} {} {}'.format(account, region, name)
        output, status = do_work([command])
        if status == 'FAILED':
            click.echo('Failed to push image to ecr, this can happen with slower internet in which case rerunning the last command "bash push_to..." allows you to still push image. You can then rerun "create-host" command with same host name and config.')
            return

        #deploy stack
        command = 'aws cloudformation deploy --template-file clean-template.json --stack-name {} --s3-bucket {}-deployment --capabilities CAPABILITY_NAMED_IAM --region {}'.format(name, name, region)
        output, status = do_work([command])
        if status == 'FAILED':
            click.echo('Failed to deploy stack in Cloudformation')
            return
    
    click.echo('STATUS: ' + status)

    if status == 'ACTIVE':
        job_api_url = None
        api_url = None
        api_key = None
        for line in output:
            if 'JOBURL' in str(line):
                parts = str(line).split(' = ')
                job_api_url = parts[-1]
            elif 'APIURL' in str(line):
                parts = str(line).split(' = ')
                api_url = parts[-1]
            elif 'APIKEY' in str(line):
                parts = str(line).split(' = ')
                api_key = parts[-1]


        ssm = boto3.client('ssm', region_name=region)

        if api_url == None:
            print('Could not find API URL in output, trying SSM Param')
            try:
                api_url = ssm.get_parameter(
                    Name=str(name + '_api_url'))
                api_url = api_url['Parameter']['Value']
            except Exception:
                print('ERROR: COULD NOT RETRIVE API URL, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
                print('CAN ALSO BE FOUND IN CF STACK OUTPUTS WITH "aws cloudformation describe-stacks --stack-name {}"'.format(name))
                pass

        if api_key == None:
            print('Could not find API KEY in output, trying SSM Param')
            try:
                api_key = ssm.get_parameter(
                    Name=str(name + '_api_key'))
                api_key = api_key['Parameter']['Value']
            except Exception:
                print('ERROR: COULD NOT RETRIVE API KEY, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
                print('CAN ALSO BE FOUND IN CF STACK OUTPUTS WITH "aws cloudformation describe-stacks --stack-name {}"'.format(name))
                pass
        if job_api_url == None:
            print('Could not find JOB API URL in output, trying SSM Param')
            try:
                job_api_url = ssm.get_parameter(
                    Name=str(name + '_job_url'))
                job_api_url = job_api_url['Parameter']['Value']
            except Exception:
                print('ERROR: COULD NOT RETRIVE JOB API URL, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
                print('CAN ALSO BE FOUND IN CF STACK OUTPUTS WITH "aws cloudformation describe-stacks --stack-name {}"'.format(name))
                pass

        host = {"name": name, "account": account, "region": region, "api_url": api_url, "api_key" : api_key, "job_api_url": job_api_url, "import_vpc": import_vpc, "vpc_id": vpc_id, "cidr": cidr}

        with open("host_credentials/{}".format(name), 'w') as outfile:
            json.dump(host, outfile)
        
        click.echo('Host credentials & config written to ./host_credentials/{}'.format(name))
        click.echo('API URL - '+ str(api_url))
        click.echo('API KEY - '+ str(api_key))
        click.echo('JOB URL - '+ str(job_api_url))

        # Set host as current for API
        with open("host_credentials/_in_use", 'w') as outfile:
            json.dump(name, outfile)
        click.echo('Host {} has been selected as current host'.format(name))
        click.echo('You can now start configuring host via hyper CLI')
        click.echo('START BY INITIALIZING YOUR MAIN REGION')

@hosts.command()
@click.pass_context
@click.option('--name', required=True, prompt='Name of host to update',  help='Name of host to update')
@click.option('--account', required=True, default=get_account(), prompt='Account it is deployed in', help='Account it is deployed in e.g. 123xxxx456')
@click.option('--region', required=True, default=get_region(), prompt='Region it is deployed in', help='Region it is deployed in, e.g. eu-west-1')
def update_host(ctx, name, account, region):
    """Any changes to your solution stacks in your local repo will be pushed to existing host"""
    client = boto3.client('ec2', region_name=region)
    try:
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:aws:cloudformation:stack-name',
                    'Values': [name]
                },
            ]
        )
        instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
    except Exception:
        click.echo(f'Could not find host {name} in account {account} in region {region}')
        return

    click.echo('')
    res = subprocess.run('docker info', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if not res.returncode == 0:
        click.echo('Docker agent not running, EXITING deployment')
        return 'Docker agent not running, EXITING deployment'
    click.echo('')
    click.echo('Building new image...')
    command3 = 'docker build -t {}.dkr.ecr.{}.amazonaws.com/{}-deploy:orchestrator .'.format(account, region, name)
    output, status = do_work([command3])
    if status == 'FAILED':
        click.echo('Failed to build image: ' + name + '-deploy')
        return

    click.echo('')
    click.echo('Pushing 4Gb Image to ECR, can take some time depending on internet')
    #build and push image to ecr for orchestrator service
    command = 'bash push_to_ecr.sh {} {} {}'.format(account, region, name)
    output, status = do_work([command])
    if status == 'FAILED':
        click.echo('Failed to push image to ecr, this can happen with slower internet in which case rerunning the last command "bash push_to..." allows you to still push image.')
        return
    
    response = client.terminate_instances(
        InstanceIds=[instance_id]
    )
    try:
        response = client.terminate_instances(
            InstanceIds=[instance_id]
        )
        click.echo(f'Terminated {instance_id} to force new image to be pulled on restart, this will take a few min to complete')
        click.echo(f'UPDATE FINISHED!')
    except Exception:
        click.echo(f'Failed to restart ec2 instance for host to update container, please terminate {instance_id} manually from concole')
        return

@hosts.command()
@click.pass_context
@click.option('--name', required=True, prompt='Give your host a name (CF stack name compliant)',  help='Give your new host a name, this becomes the stack name and all resources are associated with this')
@click.option('--account', required=True, default=get_account(), prompt='Account to deploy host to', help='AWS account to deploy host to, e.g. 123xxxx456')
@click.option('--region', required=True, default=get_region(), prompt='Region to deploy host to', callback=get_vpcs, help='AWS region to deploy host to, e.g. eu-west-1')
@click.option('--vpc', required=True, default='', prompt='If creating vpc specify cidr range to use or specify a vpc-id to import existing vpc (recommended) e.g 10.0.0.0/16 OR vpc-xxxx', help='Import or create a vpc to use by specifying either a cidr or vpc-id (e.g 10.0.0.0/16 OR vpc-xxxx)')
@click.option('--enable-dashboard', required=True, type=click.Choice(['True','False'], case_sensitive=False), prompt='[True/False] Deploy Kibana+ElasticSearch with worker & job log ingestion', help='[True/False] Deploy Kibana + ElasticSearch Cluster and data ingestion Lambdas that push all job and worker state changes to cluster. This will create a continuos cost for having solution deployed outside usage')
@click.option('--auto-init-main',required=False, default='True', type=click.Choice(['True','False'], case_sensitive=False), help='Default [True] - Automatically initialize main region when host is created, put False only if you want to use a different vpc in main region and configure this after host creation with init-main-region command')
def create_host_with_cdk(ctx, name, account, region, enable_dashboard, vpc, auto_init_main):
    """Create a new host and start configuring your clusters, queues, task definitions & images. After that you can start running jobs with qsub command"""
    res = subprocess.run('docker info', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if not res.returncode == 0:
        click.echo('Docker agent not running, EXITING deployment')
        return 'Docker agent not running, EXITING deployment'

    if 'vpc-' in vpc:
        import_vpc = 'True'
        vpc_id = vpc
        cidr='null'
        ec2 = boto3.client('ec2', region_name=region)
        vpcs = ec2.describe_vpcs()
        if not vpc in str(vpcs):
            click.echo('VpcId not found in this region')
            return 'VpcId not found in this region'
    else:
        import_vpc = 'False'
        vpc_id = 'null'
        cidr = vpc
        ec2 = boto3.client('ec2', region_name=region)
        vpcs = ec2.describe_vpcs()
        if vpc in str(vpcs):
            click.echo('CIDR already exists in this region, choose another CIDR')
            return 'CIDR already exists in this region, choose another CIDR'

    settings = {
                    "stack_settings":
                        {
                            "stack_name": name,
                            "account": account,
                            "enable_dashboard": enable_dashboard
                        }
                }

    with open("./hyper_batch/configuration/settings.json", 'w') as outfile:
        json.dump(settings, outfile)
    
    regions = {}
    regions['regions'] = []
    local_main_region = {
                        "region": region,
                        "main_region": 'True',
                        "import_vpc": import_vpc,
                        "cidr": cidr,
                        "vpc_id": vpc_id,
                        "peer_with_main_region": 'False'
                    }
    regions['regions'].append(local_main_region)

    with open("./hyper_batch/configuration/regions.json", 'w') as outfile:
        json.dump(regions, outfile)

    click.echo(' ')
    click.echo('stack_name=' + name + ' / ' + 'account=' + account + ' / ' + 'region=' + region + ' / ' 'enable_dashboard=' + enable_dashboard+ ' / ' + 'import_vpc=' + import_vpc + ' / ' + 'cidr=' + cidr + ' / ' + 'vpc_id=' + vpc_id)
    click.echo('Deploying new host.....')
    click.echo('This takes around 5 minutes...')
    output, status = create_front_end(name, region, account, enable_dashboard, import_vpc, vpc_id, cidr)
    click.echo('STATUS: ' + status)

    if status == 'ACTIVE':
        job_api_url = None
        api_url = None
        api_key = None
        for line in output:
            if 'JOBURL' in str(line):
                parts = str(line).split(' = ')
                job_api_url = parts[-1]
            elif 'APIURL' in str(line):
                parts = str(line).split(' = ')
                api_url = parts[-1]
            elif 'APIKEY' in str(line):
                parts = str(line).split(' = ')
                api_key = parts[-1]


        ssm = boto3.client('ssm', region_name=region)

        if api_url == None:
            print('Could not find API URL in output, trying SSM Param')
            try:
                api_url = ssm.get_parameter(
                    Name=str(name + '_api_url'))
                api_url = api_url['Parameter']['Value']
            except Exception:
                print('COULD NOT RETRIVE API URL, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
                pass

        if api_key == None:
            print('Could not find API KEY in output, trying SSM Param')
            try:
                api_key = ssm.get_parameter(
                    Name=str(name + '_api_key'))
                api_key = api_key['Parameter']['Value']
            except Exception:
                print('COULD NOT RETRIVE API KEY, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
                pass
        if job_api_url == None:
            print('Could not find JOB API URL in output, trying SSM Param')
            try:
                job_api_url = ssm.get_parameter(
                    Name=str(name + '_job_url'))
                job_api_url = job_api_url['Parameter']['Value']
            except Exception:
                print('COULD NOT RETRIVE API KEY, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
                pass

        host = {"name": name, "account": account, "region": region, "api_url": api_url, "api_key" : api_key, "job_api_url": job_api_url, "import_vpc": import_vpc, "vpc_id": vpc_id, "cidr": cidr}

        with open("host_credentials/{}".format(name), 'w') as outfile:
            json.dump(host, outfile)
        
        click.echo(' ')
        click.echo('Host credentials & config written to ./host_credentials/{}'.format(name))
        click.echo('API URL - '+ api_url)
        click.echo('API KEY - '+ api_key)
        click.echo('JOB URL - '+ job_api_url)

        # Set host as current for API
        with open("host_credentials/_in_use", 'w') as outfile:
            json.dump(name, outfile)
        click.echo('Host {} has been selected as current host'.format(name))
        click.echo('You can now start configuring host via hyper CLI')
        click.echo('START BY INITIALIZING YOUR MAIN REGION')

@hosts.command()
@click.pass_context
def list_hosts(ctx):
    """List existing hosts and use select-host to start making calls to this host"""
    hosts = os.listdir('host_credentials/')
    click.echo('EXISTING HOSTS:')
    click.echo(' ')
    for host in hosts:
        if not host == '_in_use':
            click.echo(host)
    try:
        host_name = get_config("./host_credentials/_in_use")
    except Exception:
        host_name = None
    click.echo('')
    click.echo('CURRENT HOST IN USE: {}'.format(host_name))
    click.echo('')
    click.echo('To select a host pass the host name to command "select-host <name to use>"')
    click.echo('')

@hosts.command()
@click.pass_context
@click.argument('host_name')
def select_host(ctx, host_name):
    """Select a host to use by passing the name of the host to this command. You can list hosts with list-hosts command"""
    host = get_config("./host_credentials/{}".format(host_name))
    with open("host_credentials/_in_use", 'w') as outfile:
            json.dump(host_name, outfile)
    click.echo('Host {} has been selected as current host'.format(host['name']))

@hosts.command()
@click.pass_context
@click.option('--name', required=True, prompt='Stack name from settings.json file',  help='Stack name from settings.json file')
@click.option('--account', required=True, default=get_account(), prompt='Account stack is deployed to', help='Account stack is deployed to')
@click.option('--region', required=True, default=get_region(), prompt='Main region used by stack', help='Main region used by stack')
def import_deployment(ctx, name, account, region):
    """If you want to import a manual cdk deployment into CLI for things like job submission, use this command"""
    ssm = boto3.client('ssm', region_name=region)

    api_url = 'null'

    try:
        api_url = ssm.get_parameter(
            Name=str(name + '_api_url'))
        api_url = api_url['Parameter']['Value']
    except Exception:
        print('COULD NOT RETRIVE API URL, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
        pass

    try:
        api_key = ssm.get_parameter(
            Name=str(name + '_api_key'))
        api_key = api_key['Parameter']['Value']
    except Exception:
        print('COULD NOT RETRIVE API KEY, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
        pass

    try:
        job_api_url = ssm.get_parameter(
            Name=str(name + '_job_url'))
        job_api_url = job_api_url['Parameter']['Value']
    except Exception:
        print('COULD NOT RETRIVE API KEY, GET MANUALLY FROM PARAMETER STORE AND UPDATE file - /host_credentials/{}'.format(name))
        pass

    host = {"name": name, "account": account, "region": region, "api_url": api_url, "api_key" : api_key, "job_api_url": job_api_url, "import_vpc": 'null', "vpc_id": 'null', "cidr": 'null'}

    with open("host_credentials/{}".format(name), 'w') as outfile:
        json.dump(host, outfile)
    
    click.echo('Host credentials & config written to ./host_credentials/{}'.format(name))
    click.echo('API URL - '+ api_url)
    click.echo('API KEY - '+ api_key)
    click.echo('JOB URL - '+ job_api_url)

    # Set host as current for API
    with open("host_credentials/_in_use", 'w') as outfile:
        json.dump(name, outfile)
    click.echo('Host {} has been selected as current host'.format(name))
    click.echo('You can now start configuring host via hyper CLI')
    click.echo('START BY INITIALIZING YOUR MAIN REGION')
            


