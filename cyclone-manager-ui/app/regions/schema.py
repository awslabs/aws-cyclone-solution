from marshmallow import Schema, fields


class RegionSchema(Schema):
    name = fields.Str(required=True)
    status = fields.Str(required=True)
    main_region = fields.Str(required=True)
    vpc_id = fields.Str(required=True)
