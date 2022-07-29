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
from gql import gql, Client # https://gql.readthedocs.io/en/latest/index.html
from gql.transport.aiohttp import AIOHTTPTransport

@click.group()
@click.pass_context
def jobs(ctx):
    """LEAVE OUT "hyper" and use following commands to manage jobs:\n
        qsub        Submit jobs, see qsub --help\n
        qstat       Query job status, see qstat --help\n
        qlog        Query progressive job log stream for SYSTEM, STDOUT, METRICS logs,\n
                    see qlog --help\n
        qdel        Delete jobs from queues, see qdel --help\n
    """
    pass

