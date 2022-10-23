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
from boto3.dynamodb.conditions import Key, Attr


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

def print_queue_short(items, filter_status, only_job_id_out, counts):
    for item in items:
        counts['Total'] = counts['Total'] + 1
        try:
            counts[item['Status']] = counts[item['Status']] + 1
        except Exception:
            counts['Error'] = counts['Error'] + 1
            pass
        
        if filter_status == None:
            if not only_job_id_out == 'True':
                click.echo(item['id'] + ' - ' + item['jobName'] + ' - ' + item['Status'] + ' - Retries left: ' + str(int(item['RetriesAvailable'])))
            else:
                click.echo(item['id'])
        if item['Status'] == filter_status:
            if not only_job_id_out == 'True':
                click.echo(item['id'] + ' - ' + item['jobName'] + ' - ' + item['Status'] + ' - Retries left: ' + str(int(item['RetriesAvailable'])))
            else:
                click.echo(item['id'])
    return counts

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
@click.option('-i', '--job-id', required=False, default=None, help='Job id to query')
@click.option('-j', '--job-name', required=False, default=None, help='Job id to query')
@click.option('-q', '--queue', required=True, default=None, help='Queue name to query')
@click.option('-f', '--filter-status', required=False, default=None, type=click.Choice(['Waiting','Running','Successful','Failed', 'Error'], case_sensitive=False), help='Filter for job status - Waiting / Running / Successful / Failed')
@click.option('-o', '--only-job-id-out', required=False, default='False', type=click.Choice(['True','False'], case_sensitive=False), help='Set True to only output job ids, can be used to pipe to other commands like qdel')
def cli(ctx, job_id, job_name, queue, filter_status, only_job_id_out):
    """qstat lets you query jobs in your queue for status updates, output and errors. 
    Inputing a job-id will do a GET and return all data on that job.
    Specifiying a job name will do a query against that job name.
    Specify only queue name will result in a scan of the whole queue (expensive). Filter for different job status 
    with --filter-status <status>. You can use the --only-job-id-out True to get a string 
    list of job ids that can then be used in a qdel operation for multiple jobs 
    e.g "qdel -q <queue> $(qstat -q <queue> --filter-status <status> --only-job-id-out true)"
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
    
    if not job_id == None:
        message = json.dumps(
                            {
                                "operation": "GET",
                                "TableName": queue,
                                "payload":{"Key": {"id": job_id}
                                }
                            }  
        )

        url = ctx.obj.url
        header = {"x-api-key" : ctx.obj.key}
        post = requests.post(url, data=message, headers=header)

        j = post.json()
        item = j['Item']
        for k, v in item.items():
            click.echo(k + ' : ' + str(v))
        return item
    elif not job_name == None:

        if filter_status == None:
            payload = {
                                    "KeyConditionExpression": '#ec4d3=:jobName',
                                    "ProjectionExpression": "#ec4d0,#ec4d1,#ec4d2,#ec4d3",
                                    "ExpressionAttributeNames": {"#ec4d0":"id","#ec4d1":"Status","#ec4d2":"RetriesAvailable","#ec4d3":"jobName"},
                                    'ExpressionAttributeValues':{":jobName":job_name},
                                    'IndexName':'index_jobName',
                                }
        else:
            payload = {
                                    "KeyConditionExpression": '#ec4d3=:jobName',
                                    "ProjectionExpression": "#ec4d0,#ec4d1,#ec4d2,#ec4d3",
                                    "ExpressionAttributeNames": {"#ec4d0":"id","#ec4d1":"Status","#ec4d2":"RetriesAvailable","#ec4d3":"jobName"},
                                    'ExpressionAttributeValues':{":jobName":job_name, ":Status":filter_status},
                                    'IndexName':'index_jobName',
                                    'FilterExpression': '#ec4d1=:Status'
                                }
        message = json.dumps(
                            {
                                "operation": "QUERY",
                                "TableName": queue,
                                "payload":payload
                            }
                            )
        
        url = ctx.obj.url
        header = {"x-api-key" : ctx.obj.key}
        post = requests.post(url, data=message, headers=header)

        j = post.json()
        
        items = j['Items']

        counts = {}
        counts['Total'] = 0
        counts['Waiting'] = 0
        counts['Running'] = 0
        counts['Successful'] = 0
        counts['Failed'] = 0
        counts['Error'] = 0
        counts = print_queue_short(items, filter_status, only_job_id_out, counts)

        while 'LastEvaluatedKey' in j:
            payload['ExclusiveStartKey'] = j['LastEvaluatedKey']
            message = json.dumps(
                            {
                                "operation": "QUERY",
                                "TableName": queue,
                                "payload":payload
                            }
                            )

            url = ctx.obj.url
            header = {"x-api-key" : ctx.obj.key}
            post = requests.post(url, data=message, headers=header)

            j = post.json()
            items = j['Items']
            counts = print_queue_short(items, filter_status, only_job_id_out, counts)

        if only_job_id_out == 'True':
            pass
        else:
            for k,v in counts.items():
                click.echo(k + ': ' + str(v))
        
    else:

        message = json.dumps(
                            {
                                "operation": "LIST",
                                "TableName": queue,
                                "payload":{
                                    "ProjectionExpression": "#ec4d0,#ec4d1,#ec4d2,#ec4d3",
                                    "ExpressionAttributeNames": {"#ec4d0":"id","#ec4d1":"Status","#ec4d2":"RetriesAvailable","#ec4d3":"jobName"},
                                }
                            }
                            )

        url = ctx.obj.url
        header = {"x-api-key" : ctx.obj.key}
        post = requests.post(url, data=message, headers=header)
        
        j = post.json()
        items = j['Items']

        counts = {}
        counts['Total'] = 0
        counts['Waiting'] = 0
        counts['Running'] = 0
        counts['Successful'] = 0
        counts['Failed'] = 0
        counts['Error'] = 0
        counts = print_queue_short(items, filter_status, only_job_id_out, counts)

        while 'LastEvaluatedKey' in j:
            message = json.dumps(
                            {
                                "operation": "LIST",
                                "TableName": queue,
                                "payload":{
                                    "ProjectionExpression": "#ec4d0,#ec4d1,#ec4d2,#ec4d3",
                                    "ExpressionAttributeNames": {"#ec4d0":"id","#ec4d1":"Status","#ec4d2":"RetriesAvailable","#ec4d3":"jobName"},
                                    "ExclusiveStartKey": j['LastEvaluatedKey']

                                }
                            }
                            )

            url = ctx.obj.url
            header = {"x-api-key" : ctx.obj.key}
            post = requests.post(url, data=message, headers=header)

            j = post.json()
            items = j['Items']
            counts = print_queue_short(items, filter_status, only_job_id_out, counts)

        if only_job_id_out == 'True':
            pass
        else:
            for k,v in counts.items():
                click.echo(k + ': ' + str(v))

if __name__ == '__main__':
    cli(obj={})