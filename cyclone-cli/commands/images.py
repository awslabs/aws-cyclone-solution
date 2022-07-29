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
import subprocess
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
    
def do_work(command_list):
    try:
        output = []
        for command in command_list:
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if 'returncode=0' in str(result):
                status = 'ACTIVE'
                output.append(result)
            else:
                status = 'FAILED'
                output.append(result)
                return output, status
        return output, status
    except subprocess.CalledProcessError as e:
        result = 'FAILED ' + str(e)
        status = 'FAILED'
        return result, status

@click.group()
@click.pass_context
def images(ctx):
    """Automated build pipeline for worker image creation. Point to a local build directory containing a Dockerfile and this image will be built and distributed across all enabled regions. When creating a task definition you can input the name of the image you want to use (make sure to use EXACTLY THE SAME NAME) and the local region image uri will be assigned to the batch job definition for that region."""
    pass

@images.command()
@click.pass_obj
@click.option('--name', required=False, default='', help='List images')
def list_images(obj, name):
    """List all images currently configured for host."""
    
    results = scan(obj.url, obj.key, obj.name +'_images_table')

    for image in results:
        if image['Status'] == 'ACTIVE':
            image['Output_Log'] = 'SUCCESSFUL'
        else:
            image['Output_Log'] = image['Output_Log']
        click.echo('---------------------------------------')
        click.echo('                            ' + image['name'])
        click.echo('---------------------------------------')
        for key in image:
            click.echo('-------------------------')
            click.echo(key)
            click.echo(image[key])
        click.echo('')

@images.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Image name', help='Give image a name')
@click.option('--local-build-directory', required=True, default='example-image-build/', prompt='Path to the local folder containing Dockerfile + dependencies for worker image', help='Name of cluster to assign to this image')
def add_image(obj, name, local_build_directory):
    """IMPORTANT: Images need to have the start.sh script, Python, AWS CLI & boto3 to work with hyper-batch. The hyper-batch automated pipeline will build the image associated with local Dockerfile directory you specify and push these out to ECR in all enabled regions. By referencing the image name in job definitions the local image within each region will be referenced in the local AWS Batch job definition."""
    
    command = 'aws s3 ls s3://{}-images-{}/images/{} --region {}'.format(obj.name, obj.region, name, obj.region)
    output, status = do_work([command])
    if status == 'ACTIVE':
        click.echo('A build directory with this name already exists in S3, give another name.')
        return 'A build directory with this name already exists in S3, give another name'

    command = 'aws s3 sync {} s3://{}-images-{}/images/{} --region {}'.format(local_build_directory, obj.name, obj.region, name, obj.region)
    output, status = do_work([command])
    if status == 'FAILED':
        click.echo('S3 upload of local directory failed: ' + str(output))
        return 'Upload to S3 Failed'
    else:
        click.echo('Local files uploaded to S3')

    # Provide a GraphQL query

    image = {
        "name": name,
        "Status": "Creating",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_images_table', image)

    click.echo('---------------------------------------')
    click.echo('                            ' + image['name'])
    click.echo('---------------------------------------')
    for key in image:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(image[key])
    click.echo('')

@images.command()
@click.pass_obj
@click.option('--name', required=True, prompt='Name of image to delete', help='image name to delete')
def delete_image(obj, name):
    """Delete an image. Specify the name as --name <name>"""    

    command = 'aws s3 rm s3://{}-images-{}/images/{} --recursive --region {}'.format(obj.name, obj.region, name, obj.region)
    output, status = do_work([command])
    if status == 'FAILED':
        click.echo('Could not delete build directory from S3 ' + str(output))


    image = {
        "name": name,
        "Status": "Deleting",
        "Output_Log": ''
    }

    post(obj.url, obj.key, obj.name +'_images_table', image)

    click.echo('---------------------------------------')
    click.echo('                            ' + image['name'])
    click.echo('---------------------------------------')
    for key in image:
        click.echo('-------------------------')
        click.echo(key)
        click.echo(image[key])
    click.echo('')