from marshmallow import Schema, fields


class JobsSchema(Schema):
    uuid = fields.Str(required=True)
    cpu_arch = fields.Str(required=True)
    cpu_brand = fields.Str(required=True)
    hostname = fields.Str(required=True)
    aws_batch_job_id = fields.Str(required=True)
    cpu_count = fields.Int(required=True)
    cpu_Hz = fields.Str(required=True)
    currenttime = fields.Str(required=True)
    id = fields.Str(required=True)
    jobdefinition = fields.Str(required=True)
    region = fields.Str(required=True)
    jobqueue = fields.Str(required=True)
    leaverunning = fields.Str(required=True)
    mem_available_gb = fields.Float(required=True)
    mem_total_gb = fields.Float(required=True)
    status = fields.Str(required=True)
