from marshmallow import Schema, fields


class QueueSchema(Schema):
    id = fields.Str(required=True)
    jobdefinition = fields.Str(required=True)
    jobname = fields.Str(required=True)
    retriesavailable = fields.Str(required=True)
    status = fields.Str(required=True)
    tcreated = fields.Str(required=True)
    terror = fields.Str(required=True)
