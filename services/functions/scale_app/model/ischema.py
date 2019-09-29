# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
from datetime import datetime

from marshmallow import Schema, fields

from .constants import IMAGE_ROOT, BUCKET

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class DeviceGroupSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'desc', 'created_at', 'updated_at')

    id = fields.UUID()
    name = fields.String()
    desc = fields.String(rename='description')
    created_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    updated_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))


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


def _image_generater(image):
    if not image:
        return None
    else:
        return os.path.join(IMAGE_ROOT, BUCKET, image)


class AppSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name', 'display_name', 'description',
                  'likes', 'stars', 'image', 'is_public')

    id = fields.Integer()
    image = fields.String(func=_image_generater)
