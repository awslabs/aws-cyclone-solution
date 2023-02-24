import json
import os
import time
from typing import Sequence
from pulumi import Input, Output
from pulumi.dynamic import Resource, ResourceProvider, CreateResult, UpdateResult, DiffResult
import requests

cyclone_name = os.environ['CYCLONE_NAME']
cyclone_account = os.environ['CYCLONE_ACCOUNT']
cyclone_main_region = os.environ['CYCLONE_MAIN_REGION']
api_key = os.environ['CYCLONE_API_KEY']
api_url = os.environ['CYCLONE_API_URL']

def get_status(name):
    message = json.dumps(
                        {
                            "operation": "GET",
                            "TableName": cyclone_name+"_clusters_table",
                            "payload":{"Key": {"name": name}
                            }
                        }  
    )

    header = {"x-api-key" : api_key}
    post = requests.post(api_url, data=message, headers=header)
    try:
        json_response = post.json()['Item']['Status']
    #only catch the actual error... if item is not in json, etc.
    except:
        json_response = None
    return json_response

class CycloneClusterArgs(object):
    name: Input[str]
    instance_list: Input[Sequence[str]]
    type: Input[str]
    allocation_strategy: Input[str]
    bid_percentage: Input[int]
    max_vCPUs: Input[int]
    compute_envs: Input[int]
    iam_policies: Input[Sequence[str]]
    main_region_image_name: Input[str]

    def __init__(
        self,
        name: Input[str],
        instance_list: Input[Sequence[str]] = ["optimal"],
        type: Input[str] = "SPOT",
        allocation_strategy: Input[str] = "SPOT_CAPACITY_OPTIMIZED",
        bid_percentage: Input[int] = 100,
        max_vCPUs: Input[int] = 1000,
        compute_envs: Input[int] = 3,
        iam_policies: Input[Sequence[str]] = [],
        main_region_image_name: Input[str] = "",
    ):
        self.name = name
        self.instance_list = instance_list
        self.type = type
        self.allocation_strategy = allocation_strategy
        self.bid_percentage = bid_percentage
        self.max_vCPUs = max_vCPUs
        self.compute_envs = compute_envs
        self.iam_policies = iam_policies
        self.main_region_image_name = main_region_image_name

def cluster_to_props(incoming_prop):
    result = {}
    for name, value in incoming_prop.items():
        if not name.startswith("_"):
            if isinstance(value, float):
                value = int(value)
            elif isinstance(value, bool):
                value = (str(value)).capitalize()
            elif isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif value is None:
                value = ""

            result[name] = value

    return result


class CycloneClusterProvider(ResourceProvider):
    def create(self, props):
        cluster = cluster_to_props(props)
        cluster["Status"] = "Creating"
        cluster["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_clusters_table",
            "payload": {"Item": cluster}
        })

        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending create to API: cyclone cluster")
        
        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Creating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error creating in AWS, check output logs: cyclone cluster")
        
        return CreateResult(props["name"], outs=props)

    def diff(self, name: str, old, props):
        replaces = []
        stables = []
        if (old["__provider"] != props["__provider"]): stables.append("__provider")
        
        return DiffResult(changes=old != props, replaces=replaces ,stables=stables, delete_before_replace=False)

    def update(self, name: str, old, props):
        cluster = cluster_to_props(props)
        cluster["name"] = name
        cluster["Status"] = "Updating"
        cluster["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_clusters_table",
            "payload": {"Item": cluster}
        })
        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending update to API: cyclone cluster")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(name)
            if status != "Updating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error updating in AWS, check output logs: cyclone cluster")

        return UpdateResult(outs={**props})


    def delete(self, name: str, props):
        cluster = cluster_to_props(props)
        cluster["name"] = name
        cluster["Status"] = "Deleting"
        cluster["Output_Log"] = ""
        
        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_clusters_table",
            "payload": {"Item": cluster}
        })

        header = {"x-api-key" : api_key}
        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending delete to API: cyclone cluster")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Deleting":
                if status == "FAILED":
                    raise Exception("Error deleting in AWS, check output logs: cyclone cluster")
                else:
                    return None


class CycloneCluster(Resource):
    name: Output[str]
    instance_list: Output[Sequence[str]]
    type: Output[str]
    allocation_strategy: Output[str]
    bid_percentage: Output[int]
    max_vCPUs: Output[int]
    compute_envs: Output[int]
    iam_policies: Output[Sequence[str]]
    main_region_image_name: Output[str]

    def __init__(self, name, args: CycloneClusterArgs, opts=None):
        super().__init__(CycloneClusterProvider(), name, vars(args), opts)