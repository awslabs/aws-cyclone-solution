from marshmallow import Schema, fields


class ClustersSchema(Schema):
    name = fields.Str(required=True)
    allocation_strategy = fields.Str(required=True)
    bid_percentage = fields.Number(required=True)
    iam_policies = fields.List(fields.Str(default=""))
    instance_list = fields.List(fields.Str(default=""))
    compute_resources_tags = fields.Dict(required=True)
    main_region_image_name = fields.Str(required=True)
    max_vcpus = fields.Number(required=True)
    status = fields.Str(required=True)
