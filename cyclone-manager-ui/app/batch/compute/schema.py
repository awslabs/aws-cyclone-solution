from marshmallow import Schema, fields


class BatchComputeSchema(Schema):
    computeEnvironmentName = fields.Str(required=True)
    computeEnvironmentArn = fields.Str(required=True)
    unmanagedvCpus = fields.Str(required=True)
    ecsClusterArn = fields.Str(required=True)
    computeResources = fields.Dict(fields.Str(required=True))
    status = fields.Str(required=True)
    statusReason = fields.Str(required=True)
