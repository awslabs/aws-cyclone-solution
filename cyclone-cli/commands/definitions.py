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
def definitions(ctx):
    """Create, update & delete task definitions to use for job submissions. REMEMBER that image names need to be an EXACT MATCH for workers to start correctly."""
    pass

@definitions.command()
@click.pass_obj
@click.option('--name', required=False, default='', help='List definitions')
def list_definitions(obj, name):
    """List all definitions currently configured for host."""
    
    results = scan(obj.url, obj.key, obj.name +'_jobDefinitions_table')

    for definition in results:
        if definition['Status'] == 'ACTIVE':
            definition['Output_Log'] = 'SUCCESSFUL'
        else:
            definition['Output_Log'] = definition['Output_Log']
        click.echo('---------------------------------------')
        click.echo('                            ' + definition['name'])
        click.echo('---------------------------------------')
        for key in definition:
            click.echo('-------------------------')
            click.echo(key)
            click.echo(definition[key])
        click.echo('')

@definitions.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Definition name', help='Give definition a name')
@click.option('--use-cyclone-image', required=True, type=click.Choice(['True','False'], case_sensitive=False), default='True', show_default=True, prompt='Use a cyclone created image or remote image', help='Use a cyclone created image or remote image [True/False]')
@click.option('--cyclone-image-name', required=False, default='', prompt='EXACT MATCH Cyclone Image Name if using this', help='OPTIONAL Cyclone Image Name if using this')
@click.option('--image-uri', required=False, default='', prompt='OPTIONAL Image uri if using remote image', help='OPTIONAL Image uri if using remote image')
@click.option('--jobs-to-workers-ratio', required=True, default=1, show_default=True, prompt='REQUIRED+IMPORTANT Ratio to control how many workers get spun up for a given number of jobs submitted, use --help', help='IMPORTANT Ratio to control how many workers get spun up for a given number of jobs submitted. Number of jobs submitted per minute (or 1000) will be divided by this ratio to decide how many additional workers to spin up for those jobs. Ratio 1 means 1 worker for every job and 50 means 1 worker created for every 50 tasks where jobs will then run in series on workers.')
@click.option('--vcpus', required=True, default=1, show_default=True, prompt='REQUIRED Number of vCPUs to use for tasks', help='REQUIRED Number of vCPUs to use for tasks')
@click.option('--memory-limit-mib', required=False, default=1024, prompt='OPTIONAL Set memory limit (mib) for tasks', help='OPTIONAL Set memory limit for tasks')
@click.option('--linux-parameters', required=False, default='', prompt='OPTIONAL Specify linux parameters, see --help for details', help='OPTIONAL Set linux parameters with e.g {"init_process_enabled": "True", "shared_memory_size": 10}')
@click.option('--ulimits', required=False, default=[], prompt='OPTIONAL Specify ulimits, see --help for details', help='OPTIONAL Set ulimits as list of jsons e.g [{"hard_limit":123, "UlimitName": "CORE", "soft_limit": 123}]')
@click.option('--mount-points', required=False, default=[], prompt='OPTIONAL Set mount points for tasks, see --help for details', help='OPTIONAL Set mount points for tasks as list of jsons e.g [{"container_path": "tmp_host", "read_only": "False", "source_volume": "volume"}]')
@click.option('--host-volumes', required=False, default=[], prompt='OPTIONAL Set host volumes for tasks, see --help for details', help='OPTIONAL Set host volumes for tasks as list of jsons e.g [{"name": "volume", "source_path": "tmp"}]')
@click.option('--gpu-count', required=False, default='', prompt='OPTIONAL Set gpu count for tasks', help='OPTIONAL Set gpu count for tasks')
@click.option('--environment', required=False, default='', prompt='OPTIONAL Set environment variables for tasks e.g {"key":"value"}', help='OPTIONAL Set environment variables for tasks e.g {"key1":"val1", "key2":"val2"}')
@click.option('--privileged', required=False, type=click.Choice(['True','False'], case_sensitive=False), default='False', show_default=True, prompt='OPTIONAL Set privileged to True to give container root access to instance', help='OPTIONAL Set privileged to True to give container root access to instance')
@click.option('--user', required=False, default='', prompt='OPTIONAL Set user to use in container', help='OPTIONAL Set user to use in container')
@click.option('--timeout_minutes', required=False, default='', prompt='OPTIONAL Set a timeout on container', help='Set a timeout on containers if you want to ensure they shut down after a certain amount of time. Keep in mind this is not a job timeout but a worker timeout as jobs run in series on the workers')
@click.option('--iam-policies', required=False, default=[], prompt='OPTIONAL Add IAM policies to worker role as list of strings e.g ["custom_policy"]', help='Add additional IAM policies to worker role (policies needed by hyper batch are automatically added)')
def add_definition(obj, name, use_cyclone_image, cyclone_image_name, image_uri, vcpus, memory_limit_mib, linux_parameters, ulimits, mount_points, host_volumes, gpu_count, environment, privileged, user, jobs_to_workers_ratio, timeout_minutes, iam_policies):
    """Add a definition to your environment, definitions will span all enabled regions."""
    iam_policies = str(iam_policies).replace("'",'"')
    environment = str(environment).replace("'",'"')
    host_volumes = str(host_volumes).replace("'",'"')
    mount_points = str(mount_points).replace("'",'"')
    ulimits = str(ulimits).replace("'",'"')
    linux_parameters = str(linux_parameters).replace("'",'"')

    definition = {
        "name": name,
        "use_cyclone_image": use_cyclone_image,
        "cyclone_image_name": cyclone_image_name,
        "image_uri": image_uri,
        "vcpus": vcpus,
        "memory_limit_mib": memory_limit_mib,
        "linux_parameters": linux_parameters,
        "ulimits": ulimits,
        "mount_points": mount_points,
        "host_volumes": host_volumes,
        "gpu_count": gpu_count,
        "environment": environment,
        "privileged": privileged,
        "user": user,
        "jobs_to_workers_ratio": jobs_to_workers_ratio,
        "timeout_minutes": timeout_minutes,
        "iam_policies": iam_policies,
        "Status": "Creating",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_jobDefinitions_table', definition)
    
    click.echo('---------------------------------------')
    click.echo('                            ' + definition['name'])
    click.echo('---------------------------------------')
    for key in definition:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(definition[key])
    click.echo('')

@definitions.command()
@click.pass_obj
@click.option('--name', required=True, help='Definition to update')
@click.option('--use-cyclone-image', required=False, help='Use a cyclone created image or remote image [True/False]')
@click.option('--cyclone-image-name', required=False, help='OPTIONAL Cyclone Image Name if using this')
@click.option('--image-uri', required=False, help='Image uri in ECR to use')
@click.option('--vcpus', required=False, help='REQUIRED Number of vCPUs to use for tasks')
@click.option('--memory-limit-mib', required=False, help='OPTIONAL Set memory limit for tasks')
@click.option('--linux-parameters', required=False, help='OPTIONAL Set linux parameters with e.g {"init_process_enabled": "True", "shared_memory_size": 10}')
@click.option('--ulimits', required=False, help='OPTIONAL Set ulimits as list of jsons e.g [{"hard_limit":123, "UlimitName": "CORE", "soft_limit": 123}]')
@click.option('--mount-points', required=False, help='OPTIONAL Set mount points for tasks')
@click.option('--host-volumes', required=False, help='OPTIONAL Set host volumes for tasks as list of jsons e.g [{"name": "volume", "source_path": "tmp"}]')
@click.option('--gpu-count', required=False, help='OPTIONAL Set gpu count for tasks')
@click.option('--environment', required=False, help='OPTIONAL Set environment variables for tasks')
@click.option('--privileged', required=False, type=click.Choice(['True','False'], case_sensitive=False), help='OPTIONAL Set privileged to True to give container root access to instance')
@click.option('--user', required=False, help='OPTIONAL Set user to use in container')
@click.option('--jobs-to-workers-ratio', required=False, help='IMPORTANT Ratio to control how many workers get spun up for a given number of jobs submitted. Number of jobs submitted per minute (or 1000) will be divided by this ratio to decide how many additional workers to spin up for those jobs. Ratio 1 means 1 worker for every job and 50 means 1 worker created for every 50 tasks where jobs will then run in series on workers.')
@click.option('--timeout_minutes', required=False, help='Set a timeout on containers if you want to ensure they shut down after a certain amount of time. Keep in mind this is not a job timeout but a worker timeout as jobs run in series on the workers')
@click.option('--iam-policies', required=False, help='Add additional IAM policies to worker role (policies needed by hyper batch are automatically added)')
def update_definition(obj, name, use_cyclone_image, cyclone_image_name, image_uri, vcpus, memory_limit_mib, linux_parameters, ulimits, mount_points, host_volumes, gpu_count, environment, privileged, user, jobs_to_workers_ratio, timeout_minutes, iam_policies):
    """Update specific configurations for an existing definition"""

    params_old = get(obj.url, obj.key, obj.name +'_jobDefinitions_table', name)

    if not use_cyclone_image == None:
        params_old['use_cyclone_image'] = use_cyclone_image
    if not cyclone_image_name == None:
        params_old['cyclone_image_name'] = cyclone_image_name
    if not image_uri == None:
        params_old['image_uri'] = image_uri
    if not vcpus == None:
        params_old['vcpus'] = vcpus
    if not memory_limit_mib== None:
        params_old['memory_limit_mib'] = memory_limit_mib
    if not linux_parameters== None:
        linux_parameters = str(linux_parameters).replace("'",'"')
        params_old['linux_parameters'] = linux_parameters
    if not ulimits== None:
        ulimits = str(ulimits).replace("'",'"')
        params_old['ulimits'] = ulimits
    if not mount_points == None:
        mount_points = str(mount_points).replace("'",'"')
        params_old['mount_points'] = mount_points
    if not host_volumes== None:
        host_volumes = str(host_volumes).replace("'",'"')
        params_old['host_volumes'] = host_volumes
    if not gpu_count == None:
        params_old['gpu_count'] = gpu_count
    if not environment == None:
        environment = str(environment).replace("'",'"')
        params_old['environment'] = environment
    if not privileged == None:
        params_old['privileged'] = privileged
    if not user == None:
        params_old['user'] = user
    if not jobs_to_workers_ratio == None:
        params_old['jobs_to_workers_ratio'] = jobs_to_workers_ratio
    if not timeout_minutes == None:
        params_old['timeout_minutes'] = timeout_minutes
    if not iam_policies == None:
        iam_policies = str(iam_policies).replace("'",'"')
        params_old['iam_policies'] = iam_policies
    params_old['Status'] ='Updating'
    params_old['Output_Log'] =''

    definition = params_old

    post(obj.url, obj.key, obj.name +'_jobDefinitions_table', definition)
    
    click.echo('---------------------------------------')
    click.echo('                            ' + definition['name'])
    click.echo('---------------------------------------')
    for key in definition:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(definition[key])
    click.echo('')

@definitions.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Name of definition to delete', help='definition name to delete')
def delete_definition(obj, name):
    """Delete a definition. Specify the name as --name <name>"""    

    params_old = get(obj.url, obj.key, obj.name +'_jobDefinitions_table', name)

    params_old['Status'] = 'Deleting'
    params_old['Output_Log'] =''

    definition = params_old

    post(obj.url, obj.key, obj.name +'_jobDefinitions_table', definition)
    
    click.echo('---------------------------------------')
    click.echo('                            ' + definition['name'])
    click.echo('---------------------------------------')
    click.echo('-------------------------')
    click.echo('Status')
    click.echo(definition['Status'])
    click.echo('')