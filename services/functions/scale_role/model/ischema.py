# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from datetime import datetime

from marshmallow import Schema, fields


class ResourceSchema(Schema):
    class Meta:
        ordered = True
        fields = ('name', 'resource_type', 'action', 'path')

    name = fields.String(attr='name')
    resource_type = fields.String(attr='resource_type')
    action = fields.String(attr='resource.action', func=lambda i: i.lower())
    path = fields.String(attr='resource.url')


class FullResourceSchema(ResourceSchema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'resource_type', 'action', 'path')

    id = fields.String()


class RoleSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')

    id = fields.Integer()
    name = fields.String()
    description = fields.String()
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, '%Y-%m-%d %H:%M:%S'))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, '%Y-%m-%d %H:%M:%S'))


class UserSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'username', 'display_name')

    id = fields.Integer()
    username = fields.String()
    display_name = fields.String()


class UserItemSchema(Schema):
    class Meta:
        ordered = True
        fields = ('uid', 'username', 'email', 'image')

    uid = fields.Integer(attr='id')
    username = fields.String()
    email = fields.String()


class UserLimitSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'type', 'max', 'seconds')

    id = fields.Integer()
    type = fields.String()
