from marshmallow import Schema, fields


class DefinitionsSchema(Schema):
    name = fields.Str()
    cyclone_image_name = fields.Str()
    enable_qlog = fields.Boolean()
    environment = fields.Dict()
    gpu_count = fields.Int()
    host_volumes = fields.List(fields.Str())
    iam_policies = fields.List(fields.Str())
    image_uri = fields.Str()
    jobs_to_workers_ratio = fields.Int()
    linux_parameters = fields.Dict()
    log_driver = fields.Str()
    log_options = fields.Dict()
    memory_limit_mib = fields.Int()
    mount_points = fields.List(fields.Str())
    privileged = fields.Boolean()
    timeout_minutes = fields.Int()
    ulimits = fields.List(fields.Dict())
    use_cyclone_image = fields.Boolean()
    user = fields.Str()
    vcpus = fields.Int()
    status = fields.Str()
    sqs_messages = fields.Number()
