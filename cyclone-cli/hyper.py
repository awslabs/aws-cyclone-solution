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
from click.termui import prompt # https://pypi.org/project/click/
import os
import json
from subprocess import Popen, PIPE
from subprocess import check_output
import requests


from commands.hosts import hosts
from commands.regions import regions
from commands.clusters import clusters
from commands.queues import queues
from commands.images import images
from commands.definitions import definitions
from commands.jobs import jobs


def get_config(json_dir):
        with open(json_dir,"r") as json_file:
            config = json.load(json_file)
            return config

class client(object):
    def __init__(self, host_name=None):
        host = get_config("./host_credentials/{}".format(host_name))
        self.url = host['api_url']
        self.key = host['api_key']
        self.region = host['region']
        self.name = host['name']
        self.import_vpc = host['import_vpc']
        self.vpc_id = host['vpc_id']
        self.cidr = host['cidr']


@click.group()
@click.version_option(0.1)
@click.pass_context
def cli(ctx):
    """WELCOME TO HYPER CLI:\n
    Hyper CLI allows you to create and manage hosts (hyper-batch control planes). Via CLI you can configure and manage resources for each host. Finally you can submit, query and delete jobs to the queues you create within a host.\n
    The CLI is divided into sections seen below in "Commands" section. Each section contains commands for managing the individual resource types, try "hyper regions" to see commands for managing regions.\n
    Creating a host deploys the control plane and needs IAM credentials. After this you use the API & API Credentials to configure resources. Deployment is asyncronous and you can check deployment status and view possible error logs via the list resources commands.\n
    GETTING STARTED:\n
    1. Start by creating a new host with the "hyper hosts create-host" command. Use "hosts create-host --help" for more details. It is common to hit limits for Elastic IPs and/or VPCs so importing a vpc can be easier.\n
    Once your host has been created the CLI will automatically load the API credentials and you can start interacting with host to configure resources.\n
    If you have multiple hosts created, use "hosts list-hosts" and "hosts select-host <host-name>" to switch between them.\n
    2. When you have created a new host you need to initiate your main region first with "hyper regions init-main-region". Check deployment status of main region with "hyper regions list-regions". It is recommended to wait for the main region to be initiated before adding additional hub regions.\n
    3. If your main region is now in Status=ACTIVE, you can start by adding your first hub region with the "hyper regions add-
    region" command and following the guided walk-through. You can add more regions, update and delete them at any time using "update-region" & "delete-region (updating network configurations can experience problems so better to delete region and recreate in that case). Use "list-regions" to view
    existing region configurations and deployment logs."\n
    4. If you are happy with regions for now move on to create your first cluster with "hyper clusters create-cluster". Clusters automatically extend across the configured regions.You can also update and delete clusters.\n
    5. Next create your first queue and map it to your cluster with "hyper queues create-queue". Remember that the cluster name used in queue config needs to be an EXACT MATCH\n
    6. You can create your first image using the example image directory /example-worker-image containing a base template Dockerfile with the start.sh script needed in all worker images. Later create your own images by referencing your own local directories with Dockerfile and build dependencies. Use the "hyper images add-image", "list-images" & "delete-image" to manage worker images.\n
    7. Next create your first job definition with "hyper definitions add-definition" using the name of your newly created image as cyclone-image-name. Remember to use an EXACT MATCH of image name. Be mindful when choosing the "jobs to workers ratio" as this will decide how many workers are started for a given number of submitted jobs (in that minute). For example a ratio of 10 means that if you submit 10 000 jobs you will request 1000 workers. Jobs run in series on workers with a matching task definition but are independent of the workers created as a result of its submission. Task definition instances are substantiated based on number of submitted jobs and the jobs to worker ratio and will run any job queued that matches its task definition until there are none left and then terminate.\n
    8. Now you are ready to start submitting and querying jobs using qsub, qstat, qlog and qdel commands WITHOUT "hyper" in front. Use "qsub --help" for more details. There is an example "qsub-example-file.sh" in root that you can use to submit your first jobs. Use "nano qsub-example-file.sh" to view the format and update the queue name and definition name to match the names you used when creating your resources. 

    SUGGESTIONS:\n
    When submitting a lot of jobs use threading, example "for i in $(seq 100); do qsub -q <queue-name> qsub_example_file.sh &; done". Be careful to not overload your workstation and use a larger instace to submit a lot of jobs quickly.\n
    You can delete multiple jobs at once by passing the output from a qstat command if you use --only-job-id-out True. Example "qdel -q <queue-name> $(qstat -q <queue-name> --only-job-id-out true)".\n
    """
    if 'host' in ctx.invoked_subcommand:
        pass
    else:
        host_name = None
        try:
            host_name = get_config("./host_credentials/_in_use")
        except Exception:
            pass
        if host_name == None:
            click.echo('You need to define a host to use. Use "list-hosts" command to see existing hosts or create a new host with "create-host"')
            click.echo('To select a host pass the host name to command "select-host <name to use>"')
            raise click.Abort()
        elif not os.path.isfile('./host_credentials/{}'.format(host_name)):
            click.echo('COULD NOT FIND HOST SPECIFIED: ' + str(host_name))
            click.echo('To select a host pass the host name to command "select-host <name to use>"')
            click.echo('Use "list-hosts" command to see existing hosts or create a new host with "create-host"')
            raise click.Abort()
        else:
            ctx.obj = client(host_name)

cli.add_command(hosts)
cli.add_command(regions)
cli.add_command(clusters)
cli.add_command(queues)
cli.add_command(images)
cli.add_command(definitions)
cli.add_command(jobs)

if __name__ == '__main__':
    cli(obj={})
