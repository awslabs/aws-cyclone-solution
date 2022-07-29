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


"""
Entry point for the CLI
"""

import click
import json
import os
import json
import requests
from requests.auth import HTTPBasicAuth


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

class client(object):
    def __init__(self, host_name=None):
        host = get_config("./host_credentials/{}".format(host_name))
        self.url = host['job_api_url']
        self.region = host['region']
        self.name = host['name']
        self.key = host['api_key']
        self.vpc_id = host['vpc_id']
        self.cidr = host['cidr']


@click.command()
@click.pass_context
@click.option('-j', '--job-name', required=False, default=None, help='Name for job group being submitted (each task gets assigned unique id)')
@click.option('-q', '--queue', required=False, default=None, help='Name for job group being submitted (each task gets assigned unique id)')
@click.option('-r', '--retries', required=False, default=None, help='Name for job group being submitted (each task gets assigned unique id)')
@click.option('-d', '--definition', required=False, default=None, help='Name for job group being submitted (each task gets assigned unique id)')
@click.option('-c', '--commands', required=False, default=None, help='Name for job group being submitted (each task gets assigned unique id)')
@click.argument('filename', type=click.Path(exists=True))
def cli(ctx, job_name, queue, retries, definition, commands, filename):
    """Submit jobs using "qsub file_name.sh" (DON'T INCLUDE "hyper") using the file format shown in qsub_example_file.sh found in repo root directory.
    You can also override configurations in the file when submitting jobs via the qsub command option parameters.
    You can query job status with qstat and delete jobs in queue with qdel. You can view logs with qlog. Use "nano qsub_example_file.sh" to see the file format for job submits and update configurations.
    Try "qsub qsub_example_file.sh" to submit a job. 
    """
    host_name = None
    try:
        host_name = get_config("./host_credentials/_in_use")
    except Exception:
        pass
    if host_name == None:
        click.echo('You need to define a host to use. Use "list-hosts" command to see existing hosts or create a new host with "create-host"')
        click.echo('To select a host pass the host name to command "select-host <name to use>"')
        click.Abort
    elif not os.path.isfile('./host_credentials/{}'.format(host_name)):
        click.echo('COULD NOT FIND HOST SPECIFIED')
        click.echo('To select a host pass the host name to command "select-host <name to use>"')
        click.echo('Use "list-hosts" command to see existing hosts or create a new host with "create-host"')
    else:
        ctx.obj = client(host_name)
    
        message = {
        "operation": "POST",
        "TableName": None,
        "Item":{   
                    "jobName": None,
                    "jobQueue": None,
                    "RetriesAvailable": None,
                    "jobDefinition": None,
                    "commands": None
                    }
        
    }  

    with open(filename,"r") as file:
        message['Item']['commands'] = file.read()

    lines = message['Item']['commands'].splitlines()
    for line in lines:
        if '#HYPER -n' in line:
            message['Item']['jobName'] = line.replace('#HYPER -n ', '')
        elif '#HYPER -q' in line:
            message['Item']['jobQueue'] = line.replace('#HYPER -q ', '')
        elif '#HYPER -r' in line:
            message['Item']['RetriesAvailable'] = line.replace('#HYPER -r ', '')
        elif '#HYPER -d' in line:
            message['Item']['jobDefinition'] = line.replace('#HYPER -d ', '')


    
    if not job_name == None:
        message['Item']['jobName'] = job_name
    if not queue == None:
        message['Item']['jobQueue'] = queue
    if not retries == None:
        message['Item']['RetriesAvailable'] = retries
    if not definition == None:
        message['Item']['jobDefinition'] = definition
    if not commands == None:
        message['Item']['commands'] = commands

    for k, v in message['Item'].items():
        if v == None:
            click.echo('Need to specify value for ' + k)
            return print('Aborted')

    
    message['Item']['RetriesAvailable'] = int(message['Item']['RetriesAvailable'])
    message['TableName'] = message['Item']['jobQueue']

    url = ctx.obj.url
    auth = HTTPBasicAuth('apikey', ctx.obj.key)
    post = requests.post(url, auth=auth, data=json.dumps(message))
    j = post.json()
    
    try:
        job_id = j['job_id']
        click.echo(job_id)
        return job_id
    except Exception:
        click.echo('FAILED - ' + str(j))
        pass

if __name__ == '__main__':
    cli(obj={})
