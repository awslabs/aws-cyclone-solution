import json
import time
import os
from typing import Any, Mapping
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
                            "TableName": cyclone_name+"_queues_table",
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

class CycloneQueueArgs(object):
    name: Input[str]
    computeEnvironment: Input[str]
    optimise_lowest_spot_cost_region: Input[bool]
    region_distribution_weights: Input[Mapping[str, Any]]

    def __init__(
        self,
        name: Input[str],
        computeEnvironment: Input[str],
        optimise_lowest_spot_cost_region: Input[bool] = True,
        region_distribution_weights: Input[Mapping[str, Any]] = {"us-east-1": "auto"},
    ):
        self.name = name
        self.computeEnvironment = computeEnvironment
        self.optimise_lowest_spot_cost_region = optimise_lowest_spot_cost_region
        self.region_distribution_weights = region_distribution_weights

def queue_to_props(incoming_prop):
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


class CycloneQueueProvider(ResourceProvider):
    def create(self, props):
        queue = queue_to_props(props)
        queue["Status"] = "Creating"
        queue["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_queues_table",
            "payload": {"Item": queue}
        })

        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending create to API: cyclone queue")
        
        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Creating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error creating in AWS, check output logs: cyclone queue")
        
        return CreateResult(props["name"], outs=props)


    def diff(self, name: str, old, props):
        replaces = []
        stables = []
        if (old["__provider"] != props["__provider"]): stables.append("__provider")
        
        return DiffResult(changes=old != props, replaces=replaces ,stables=stables, delete_before_replace=False)


    def update(self, name: str, old, props):
        queue = queue_to_props(props)
        queue["name"] = name
        queue["Status"] = "Updating"
        queue["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_queues_table",
            "payload": {"Item": queue}
        })
        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending update to API: cyclone queue")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(name)
            if status != "Updating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error updating in AWS, check output logs: cyclone queue")

        return UpdateResult(outs={**props})


    def delete(self, name: str, props):
        queue = queue_to_props(props)
        queue["name"] = name
        queue["Status"] = "Deleting"
        queue["Output_Log"] = ""
        
        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_queues_table",
            "payload": {"Item": queue}
        })

        header = {"x-api-key" : api_key}
        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending delete to API: cyclone queue")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Deleting":
                if status == "FAILED":
                    raise Exception("Error deleting in AWS, check output logs: cyclone queue")
                else:
                    return None


class CycloneQueue(Resource):
    name: Output[str]
    computeEnvironment: Output[str]
    optimise_lowest_spot_cost_region: Output[bool]
    region_distribution_weights: Output[Mapping[str, Any]]

    def __init__(self, name, args: CycloneQueueArgs, opts=None):
        super().__init__(CycloneQueueProvider(), name, vars(args), opts)