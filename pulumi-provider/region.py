import json
import time
import os
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
                            "TableName": cyclone_name+"_regions_table",
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

class CycloneRegionArgs(object):
    name: Input[str]
    main_region: Input[bool]
    import_vpc: Input[bool]
    cidr: Input[str]
    vpc_id: Input[str]
    peer_with_main_region: Input[bool]
    deploy_vpc_endpoints: Input[str]

    def __init__(
        self,
        name: Input[str],
        main_region: Input[bool] = False,
        import_vpc: Input[bool] = True,
        cidr: Input[str] = "null",
        vpc_id: Input[str] = "",
        peer_with_main_region: Input[bool] = False,
        deploy_vpc_endpoints: Input[str] = "OFF",
    ):
        self.name = name
        self.main_region = main_region
        self.import_vpc = import_vpc
        self.cidr = cidr
        self.vpc_id = vpc_id
        self.peer_with_main_region = peer_with_main_region
        self.deploy_vpc_endpoints = deploy_vpc_endpoints

def region_to_props(incoming_prop):
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


class CycloneRegionProvider(ResourceProvider):
    def create(self, props):
        region = region_to_props(props)
        region["Status"] = "Creating"
        region["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_regions_table",
            "payload": {"Item": region}
        })

        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending create to API: cyclone region")
        
        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Creating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error creating in AWS, check output logs: cyclone region")
        
        return CreateResult(props["name"], outs=props)

    def diff(self, name: str, old, props):
        replaces = []
        stables = []
        if (old["__provider"] != props["__provider"]): stables.append("__provider")
        
        return DiffResult(changes=old != props, replaces=replaces ,stables=stables, delete_before_replace=False)

    def update(self, name: str, old, props):
        region = region_to_props(props)
        region["name"] = name
        region["Status"] = "Updating"
        region["Output_Log"] = ""

        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_regions_table",
            "payload": {"Item": region}
        })
        header = {"x-api-key" : api_key}

        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending update to API: cyclone region")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(name)
            if status != "Updating":
                if status == "ACTIVE":
                    active = True
                else:
                    raise Exception("Error updating in AWS, check output logs: cyclone region")

        return UpdateResult(outs={**props})


    def delete(self, name: str, props):
        region = region_to_props(props)
        region["name"] = name
        region["Status"] = "Deleting"
        region["Output_Log"] = ""
        
        data = json.dumps({
            "operation": "POST",
            "TableName": cyclone_name+"_regions_table",
            "payload": {"Item": region}
        })

        header = {"x-api-key" : api_key}
        response = requests.post(api_url, data=data, headers=header)
        if response.status_code != 200:
            raise Exception("Error sending delete to API: cyclone region")

        active = False
        while not active:
            time.sleep(10)
            status = get_status(props["name"])
            if status != "Deleting":
                if status == "FAILED":
                    raise Exception("Error deleting in AWS, check output logs: cyclone region")
                else:
                    return None


class CycloneRegion(Resource):
    name: Output[str]
    main_region: Output[bool]
    import_vpc: Output[bool]
    cidr: Output[str]
    vpc_id: Output[str]
    peer_with_main_region: Output[bool]
    deploy_vpc_endpoints: Output[str]

    def __init__(self, name, args: CycloneRegionArgs, opts=None):
        super().__init__(CycloneRegionProvider(), name, vars(args), opts)