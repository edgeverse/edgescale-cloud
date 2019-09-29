# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP


from datetime import datetime

from marshmallow import Schema, fields

from .constants import TASK_TYPE_NAMES, TASK_STATUS_NAMES


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def strftime(dt):
    if dt:
        return datetime.strftime(dt, DATETIME_FORMAT)
    else:
        return None


class TaskSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'type', 'status', 'created_at', 'started_at', 'ended_at', 'payloads')

    type = fields.String(func=lambda n: TASK_TYPE_NAMES[n])
    payloads = fields.String(rename='payload', attr='payloads')
    status = fields.String(func=lambda st: TASK_STATUS_NAMES[st])
    created_at = fields.DateTime(rename='create_time', attr='created_at', func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    started_at = fields.DateTime(func=lambda dt: datetime.strftime(dt, DATETIME_FORMAT))
    ended_at = fields.DateTime(func=strftime)


class ShortDeviceSchema(Schema):
    class Meta:
        ordered = True
        fields = ('id', 'name')
