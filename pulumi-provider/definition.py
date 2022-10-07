import json
import time
import os
from typing import Dict, List
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
                            "TableName": cyclone_name+"_jobDefinitions_table",
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

class CycloneDefinitionArgs(object):
    name: Input[str]
    use_cyclone_image: Input[bool]
    cyclone_image_name: Input[str]
    image_uri: Input[str]
    vcpus: Input[int]
    memory_limit_mib: Input[int]
    linux_parameters: Input[str]
    ulimits: Input[List[str]]
    mount_points: Input[List[str]]
    host_volumes: Input[List[str]]
    gpu_count: Input[int]
    environment: Input[Dict[str,str]]
    privileged: Input[bool]
    user: Input[str]
    jobs_to_workers_ratio: Input[int]
    timeout_minutes: Input[int]
    iam_policies: Input[List[str]]
    log_driver: Input[str]
    log_options: Input[Dict[str,str]]
    enable_qlog: Input[bool]

    def __init__(
        self,
        name: Input[str],
        use_cyclone_image: Input[bool] = False,
        cyclone_image_name: Input[str] = "",
        image_uri: Input[str] = "",
        vcpus: Input[int] = 1,
        memory_limit_mib: Input[int] = 2048,
        linux_parameters: Input[str] = "",
        ulimits: Input[List[str]] = [],
        mount_points: Input[List[str]] = [],
        host_volumes: Input[List[str]] = [],
        gpu_count: Input[int] = "",
        environment: Input[Dict[str,str]] = {"LOG_LEVEL": "INFO", "JSON_LOGGING": "True"},
        privileged: Input[bool] = False,
        user: Input[str] = "",
        jobs_to_workers_ratio: Input[int] = 1,
        timeout_minutes: Input[int] = "",
        iam_policies: Input[List[str]] = [],
        log_driver: Input[str] = "JSON_FILE",
        log_options: Input[Dict[str,str]] = {"max-size": "10m", "max-file": "3"},
        enable_qlog: Input[bool] = False,
    ):
        self.name = name
        self.use_cyclone_image = use_cyclone_image
        self.cyclone_image_name = cyclone_image_name
        self.image_uri = image_uri
        self.vcpus = vcpus
        self.memory_limit_mib = memory_limit_mib
        self.linux_parameters = linux_parameters
        self.ulimits = ulimits
        self.mount_points = mount_points
        self.host_volumes = host_volumes
        self.gpu_count = gpu_count
        self.environment = environment
        self.privileged = privileged
        self.user = user
        self.jobs_to_workers_ratio = jobs_to_workers_ratio
        self.timeout_minutes = timeout_minutes
        self.iam_policies = iam_policies
        self.log_driver = log_driver
        self.log_options = log_options
        self.enable_qlog = enable_qlog

def definition_to_props(incoming_prop):
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


class CycloneDefinitionProvider(ResourceProvider):
    def create(self, props):
        definition = definition_to_props(props)
        definition["Status"] = "Creating"
        definition["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_jobDefinitions_table",
            "payload": {"Item": definition}
        })

        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending create to API: cyclone definition")
        
        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Creating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error creating in AWS, check output logs: cyclone definition")
        
        return CreateResult(props["name"], outs=props)

    def diff(self, name: str, old, props):
        replaces = []
        stables = []
        if (old["__provider"] != props["__provider"]): stables.append("__provider")
        
        return DiffResult(changes=old != props, replaces=replaces ,stables=stables, delete_before_replace=False)

    def update(self, name: str, old, props):
        definition = definition_to_props(props)
        definition["name"] = name
        definition["Status"] = "Updating"
        definition["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_jobDefinitions_table",
            "payload": {"Item": definition}
        })
        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending update to API: cyclone definition")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(name)
            if status != "Updating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error updating in AWS, check output logs: cyclone definition")

        return UpdateResult(outs={**props})


    def delete(self, name: str, props):
        definition = definition_to_props(props)
        definition["name"] = name
        definition["Status"] = "Deleting"
        definition["Output_Log"] = ""
        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_jobDefinitions_table",
            "payload": {"Item": definition}
        })

        header = {"x-api-key" : api_key}
        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending delete to API: cyclone definition")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Deleting":
                if status == "FAILED":
                    raise Exception("Error deleting in AWS, check output logs: cyclone definition")
                else:
                    return None


class CycloneDefinition(Resource):
    name: Output[str]
    use_cyclone_image: Output[bool]
    cyclone_image_name: Output[str]
    image_uri: Output[str]
    vcpus: Output[int]
    memory_limit_mib: Output[int]
    linux_parameters: Output[str]
    ulimits: Output[List[str]]
    mount_points: Output[List[str]]
    host_volumes: Output[List[str]]
    gpu_count: Output[int]
    environment: Output[Dict[str,str]]
    privileged: Output[bool]
    user: Output[str]
    jobs_to_workers_ratio: Output[int]
    timeout_minutes: Output[int]
    iam_policies: Output[List[str]]
    log_driver: Output[str]
    log_options: Output[Dict[str,str]]
    enable_qlog: Output[bool]

    def __init__(self, name, args: CycloneDefinitionArgs, opts=None):
        super().__init__(CycloneDefinitionProvider(), name, vars(args), opts)