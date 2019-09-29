# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from datetime import datetime

from marshmallow import Schema, fields

from edgescale_pymodels.constants import DATETIME_FORMAT


class DeviceGroupSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'desc', 'created_at', 'updated_at')

    id = fields.UUID()
    name = fields.String()
    desc = fields.String(rename='description')
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))


class DeviceGroupBindSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name','desc')

    id = fields.UUID()
    name = fields.String()
    desc = fields.String(rename='description')


class DeviceIDSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id','name')
    id = fields.Integer()
    name = fields.String()


class ModelSchema(Schema):
    class Meta:
        Ordered = True
        fields = ('model','type', 'platform', 'vendor')

    model = fields.String()
    type = fields.String()
    platform = fields.String()
    vendor = fields.String()


class DeviceSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id','name','created_at','owner_id','certname','dcca_model_id','display_name')

    id = fields.Integer()
    name = fields.String()
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    owner_id = fields.Integer()
    certname = fields.String()
    dcca_model_id = fields.Nested(ModelSchema)
    display_name = fields.String()


class TaskSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'type', 'status', 'created_at', 'payloads')

    created_at = fields.DateTime(rename='create_time', attr='created_at', func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    payloads = fields.String(rename='payload', attr='payloads')
