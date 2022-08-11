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
@click.argument('job-ids', nargs=-1)
def cli(ctx, job_ids, queue):
    """Enter job Ids you would like to delete. You can use "only-job-id-out=True" in a qstat query to then pass 
    results to qdel e.g "qdel -q <queue> $(qstat -q <queue> --filter-status <status> --only-job-id-out true)" 
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
    if len(job_ids) < 1:
        click.echo('No job ids provided, use qdel -q <queue-name> <id1> <id2>')
        return
    for job_id in job_ids:
        list = job_id.splitlines()
        for job_id in list:
    
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
                click.echo('Successfully Deleted: ' + job_id)
            else:
                click.echo('FAILED: ' + j)
    return j

if __name__ == '__main__':
    cli(obj={})