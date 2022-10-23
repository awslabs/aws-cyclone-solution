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
@click.option('-q', '--queue', required=True, default=None, help='Name of queue to delete jobs from')
@click.option('-i', '--job-id', required=False, default=None, help='Job id to delete')
@click.option('-j', '--job-name', required=False, default=None, help='Job name batch deletion')
def cli(ctx, queue, job_id, job_name):
    """Enter job id to delete or enter a job name to do a batch deletion. If you have a lot of jobs in queue you can run the qdel commands multiple times to have multiple lambdas deleting a job name in background. 
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

    if not job_name == None:
        message = json.dumps(
                    {
                        "operation": "DELETE",
                        "TableName": queue,
                        "payload":{"Key": {"job_name": job_name}
                        }
                    }  
        )
        url = ctx.obj.url
        header = {"x-api-key" : ctx.obj.key}
        post = requests.post(url, data=message, headers=header)
        j = post.json()
        try:
            if j['message'] == 'Endpoint request timed out':
                click.echo('Lambda is continuing deleting in background, run command again to increase parallel delete operations')
                return
        except Exception:
            pass
        if j['ResponseMetadata']['HTTPStatusCode'] == 200:
            click.echo('Successfully Deleted Job Name: ' + job_name)
            return
        else:
            click.echo('FAILED: ' + j)

    elif not job_id == None:
    
            message = json.dumps(
                                {
                                    "operation": "DELETE",
                                    "TableName": queue,
                                    "payload":{"Key": {"id": job_id}
                                    }
                                }  
            )
            
            url = ctx.obj.url
            header = {"x-api-key" : ctx.obj.key}
            post = requests.post(url, data=message, headers=header)
            j = post.json()
            if j['ResponseMetadata']['HTTPStatusCode'] == 200:
                click.echo('Successfully Deleted Job ID: ' + job_id)
                return
            else:
                click.echo('FAILED: ' + j)
    return j

if __name__ == '__main__':
    cli(obj={})