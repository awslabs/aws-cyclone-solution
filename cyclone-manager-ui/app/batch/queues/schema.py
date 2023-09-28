from marshmallow import Schema, fields


class BatchQueueSchema(Schema):
    jobQueueName = fields.Str(required=True)
    state = fields.Str(required=True)
    jobQueueArn = fields.Str(required=True)
    status = fields.Str(required=True)
    statusReason = fields.Str(required=True)
    computeEnvironmentOrder = fields.List(fields.Dict())
