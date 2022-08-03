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

from datetime import datetime
import json
import os
import requests
from requests.auth import HTTPBasicAuth


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

def get_timestamp(elem):
    return datetime.fromisoformat(elem['time_stamp'])

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
@click.option('-i', '--job-id', required=True, default=None, help='Job_Id for job to query')
@click.option('-q', '--queue', required=True, default=None, help='Queue that job is in')
@click.option('-t', '--log-type', required=False, type=click.Choice(['', 'STDOUT','METRICS', 'SYSTEM'], case_sensitive=False), default='', help='Log type to query, options are SYSTEM / STDOUT / METRICS)')
def cli(ctx, job_id, queue, log_type):
    """qlog command allows you to query progressive log stream from jobs including SYSTEM logs for debugging, STDOUT logs from job execution and METRIC logs for vCPU and vRAM consumption at 10s intervals.
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
    
    bucket_name = ctx.obj.name + '-images-' + ctx.obj.region
    message = json.dumps(
                        {
                            "operation": "GET_KEYS",
                            "TableName": queue,
                            "payload":{"bucket": bucket_name, "id": job_id}
                        }  
    )

    url = ctx.obj.url
    header = {"x-api-key" : ctx.obj.key}
    post = requests.post(url, data=message, headers=header)

    j = post.json()
    log_full = []
    for key in j:
        message = json.dumps(
                        {
                            "operation": "GET_LOG",
                            "TableName": queue,
                            "payload":{"bucket": bucket_name, "key": key}
                        }  
            )
        post = requests.post(url, auth=auth, data=message)
        log_raw = post.json()
        for line in log_raw['data']:
            if log_type in line['log_type']:
                log_full.append(line)

    logs_sorted = sorted(log_full, key=get_timestamp, reverse=False)
    for line in logs_sorted:
        click.echo(line['log_type'] + ' | ' + line['time_stamp'] + ' | ' + str(line['data']))
    
    return

if __name__ == '__main__':
    cli(obj={})
