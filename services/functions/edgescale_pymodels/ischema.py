# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from datetime import datetime

from marshmallow import Schema, fields


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
REQUEST_STATUS = {0: 'Pending', 1: 'Approved', 2: 'Rejected'}


class ModelEngineSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'type', 'is_public', 'created_at', 'updated_at', 'description', 'url')

    id = fields.UUID()
    name = fields.String()
    type = fields.String(attr='category')
    is_public = fields.Boolean()
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    desc = fields.String()
    url = fields.String()


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


class AccountSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'company_name', 'telephone', 'email', 'job_title', 'account_type',
                  'first_name', 'last_name', 'created_at', 'status')

    id = fields.Integer()
    company_name = fields.String()
    telephone = fields.String()
    email = fields.Email()
    job_title = fields.String()
    account_type = fields.String(attr='account_type.name')
    first_name = fields.String()
    last_name = fields.String()
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    status = fields.String(func=lambda status: REQUEST_STATUS[status])


class TemplateAppSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'type', 'created_at', 'updated_at', 'description')

    id = fields.UUID()
    name = fields.String()
    type = fields.String(attr='category')
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    desc = fields.String()


class DeviceGroupSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'desc', 'created_at', 'updated_at')

    id = fields.UUID()
    name = fields.String()
    desc = fields.String(rename='description')
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))


class CustomerSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'is_active', 'created_at', 'updated_at', 'description')

    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))


class DeviceShortSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name')


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
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))


class VendorSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'is_public', 'created_at', 'updated_at')

    id = fields.Integer()
    name = fields.String()
    is_public = fields.Boolean()
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
