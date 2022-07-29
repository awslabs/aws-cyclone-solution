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

import boto3
import os
from aws_xray_sdk.core import patch_all
import logging
import json
import jsonpickle

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.ERROR)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
patch_all()


main_region = os.environ.get('MAIN_REGION')
hub_cidr = os.environ.get('HUB_CIDR')
peering_id = os.environ.get('PEERING_ID')
main_vpc_id = os.environ.get('MAIN_VPC_ID')

ec2 = boto3.client('ec2', region_name=main_region)

def lambda_handler(event, context):

    logger.info('## ENVIRONMENT VARIABLES\r' + jsonpickle.encode(dict(**os.environ)))
    logger.info('## EVENT\r' + jsonpickle.encode(event))
    logger.info('## CONTEXT\r' + jsonpickle.encode(context))

    vpcs = ec2.describe_vpcs()
    if not main_vpc_id in str(vpcs):
        raise Exception(f'Invalid vpc id: {main_vpc_id}')
    
    subnets = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    main_vpc_id
                ]
            }
        ])
    private_table_ids = []

    for subnet in subnets['Subnets']:
        subnet_id = subnet['SubnetId']
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
                add = True
                for route in routeTable['Routes']:
                    try:
                        if 'igw-' in route['GatewayId']:
                            add = False
                    except Exception:
                        pass
                if add:
                    private_table_ids.append(routeTable['RouteTableId'])
        else:
            route_tables = ec2.describe_route_tables(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        main_vpc_id,
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
                add = True
                for route in routeTable['Routes']:
                    try:
                        if 'igw-' in route['GatewayId']:
                            add = False
                    except Exception:
                        pass
                if add:
                    private_table_ids.append(routeTable['RouteTableId'])
    

    private_table_ids = list(dict.fromkeys(private_table_ids))

    request_type = event['RequestType'].lower()
    if request_type == 'create':
        return on_create(event, private_table_ids)
    if request_type == 'update':
        return on_update(event, private_table_ids)
    if request_type == 'delete':
        return on_delete(event, private_table_ids)
    raise Exception(f'Invalid request type: {request_type}')

def on_create(event, private_table_ids):
    if not len(private_table_ids) > 0:
        logger.error('## No private subnets found in main region to peer with:\r' + jsonpickle.encode(main_vpc_id))
        raise ValueError(f'No private subnets found in main region to peer with: {main_vpc_id}')
    response = ec2.modify_vpc_peering_connection_options(
        AccepterPeeringConnectionOptions={
            'AllowDnsResolutionFromRemoteVpc': True
        },
        VpcPeeringConnectionId=peering_id
    )

    for routeTableId in private_table_ids:

        try:
            response = ec2.create_route(
                DestinationCidrBlock=hub_cidr,
                RouteTableId=routeTableId,
                VpcPeeringConnectionId=peering_id
            )
        except Exception:
            if "RouteAlreadyExists" in response:
                response = ec2.replace_route(
                    DestinationCidrBlock=hub_cidr,
                    RouteTableId=routeTableId,
                    VpcPeeringConnectionId=peering_id
                )
            pass

    return json.dumps({'PhysicalResourceId': 'main_region_route'})

def on_update(event,private_table_ids):
    if not len(private_table_ids) > 0:
        raise ValueError(f'No private subnets found in main region to peer with: {main_vpc_id}')
    response = ec2.modify_vpc_peering_connection_options(
        AccepterPeeringConnectionOptions={
            'AllowDnsResolutionFromRemoteVpc': True
        },
        VpcPeeringConnectionId=peering_id
    )

    for routeTableId in private_table_ids:
        try:
            response = ec2.replace_route(
                DestinationCidrBlock=hub_cidr,
                RouteTableId=routeTableId,
                VpcPeeringConnectionId=peering_id
            )
        except Exception:
            pass
    

    return json.dumps({'PhysicalResourceId': 'main_region_route'})

def on_delete(event,private_table_ids):
    response = ec2.modify_vpc_peering_connection_options(
        AccepterPeeringConnectionOptions={
            'AllowDnsResolutionFromRemoteVpc': False
        },
        VpcPeeringConnectionId=peering_id
    )

    for routeTableId in private_table_ids:

        response = ec2.delete_route(
            DestinationCidrBlock=hub_cidr,
            RouteTableId=routeTableId,
        )

    return json.dumps({'PhysicalResourceId': 'main_region_route'})
