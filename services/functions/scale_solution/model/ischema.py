# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from marshmallow import Schema, fields

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class TagsSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name')


class ModelSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'model', 'type', 'platform', 'vendor', 'owner_id', 'default_solution_id')


class ModelShortSchema(Schema):
    class Meta:
        ordered = True
        fields = ('model', 'type', 'platform', 'vendor')


class SolutionSchema(Schema):
    model = fields.Nested(ModelSchema())
    tags = fields.Nested(TagsSchema(), many=True)

    class Meta:
        ordered = True
        fields = ('id', 'solution', 'image', 'version', 'link', 'is_public', 'in_s3', 'is_signed',
                  'owner_id', 'model', 'tags')


class SolutionShortSchema(Schema):
    name = fields.String(attribute="solution")

    class Meta:
        ordered = True
        fields = ('id', 'name')


class DeviceSchema(Schema):
    created_at = fields.DateTime(DATETIME_FORMAT)
    model = fields.Nested(ModelShortSchema)

    class Meta:
        ordered = True
        fields = ('id', 'name', 'created_at', 'display_name', 'model')


class DeviceShortSchema(Schema):
    solution = fields.Nested(SolutionShortSchema())

    class Meta:
        ordered = True
        fields = ('id', 'solution')


class UserShortSchema(Schema):
    name = fields.String(attribute="username")

    class Meta:
        ordered = True
        fields = ('name',)


class SolutionAuditSchema(Schema):
    created_at = fields.DateTime(DATETIME_FORMAT)
    solution = fields.Nested(SolutionShortSchema())
    user = fields.Nested(UserShortSchema())

    class Meta:
        ordered = True
        fields = ('id', 'created_at', 'approved', 'comments', 'status', 'solution', 'user')

