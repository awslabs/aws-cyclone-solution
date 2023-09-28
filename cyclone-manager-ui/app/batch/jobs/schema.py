from marshmallow import Schema, fields


class BatchJobSchema(Schema):
    jobArn = fields.Str(required=True)
    jobName = fields.Str(required=True)
    jobId = fields.Str(required=True)
    status = fields.Str(required=True)
    statusReason = fields.Str(required=True)
