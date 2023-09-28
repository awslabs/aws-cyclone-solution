from marshmallow import Schema, fields


class QueuesSchema(Schema):
    name = fields.Str(required=True)
    computeenvironment = fields.Str(required=True)
    optimise_lowest_spot_cost_region = fields.Bool(required=True)
    status = fields.Str(required=True)
    region_distribution_weights = fields.Dict(required=True)
