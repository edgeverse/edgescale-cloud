# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import namedtuple

BUCKET = 'dcca-images'
IMAGE_ROOT = 'https://s3-us-west-2.amazonaws.com/dcca-images'
IMAGE_DEFAULT_NAME = ''

TIME_FORMAT_STR = "%Y-%m-%d %H:%M:%S"

MSG_NOT_APP = 'This app does not exist.Or not in the app store.'

MSG_NOT_APP_NAME = 'This app already exists in your app. Please do not repeat!!'

MSG_NOT_APP_OWNER = 'Not the owner or APP not exist'

Application = namedtuple('Application', ['id', 'name', 'display_name', 'description',
                                         'likes', 'stars', 'image', 'is_public', 'owner'])

ApplicationShort = namedtuple('ApplicationShort', ['id', 'name', 'display_name', 'description',
                                                   'likes', 'stars', 'image', 'is_public', 'owner'])

AppObj = namedtuple('AppObj', ['id', 'version', 'registry_id', 'image_name', 'commands', 'args', 'arguments'])
AppArguments = namedtuple('AppArguments', ['host_network', 'ports', 'volumes', 'volume_mounts', 'cap_add', 'morepara'])
ApplicationTag = namedtuple('ApplicationTag', ['app_id', 'tag_id', 'tag_name'])
AppShort = namedtuple('AppShort', ['id', 'version',
                                   'registry_id', 'image_name',
                                   'commands', 'args',
                                   'host_network', 'ports',
                                   'volumes', 'volume_mounts',
                                   'cap_add', 'morepara'])
Mirror = namedtuple('Mirror', ['id', 'name', 'public', 'desc'])


PARSED_PATH_MAPPING = [{"hostPath": "", "mountPath": "", "mountPathReadOnly": False}]


DEFAULT_REGISTRY_ID = 5
AUDIT_REQUEST_STATUS = 1

EMPTY_PORTS_MAPPING = [{"containerPort": '', "hostPort": ""}]
EMPTY_VOLUMES_MAPPING = [{"hostPath": {"path": ""}, "name": ""}]
EMPTY_VOLUME_MOUNTS_MAPPING = [{"readOnly": False, "mountPath": "", "name": ""}]

UNAUTH_RESULT = {
    "error": True,
    "status": "fail",
    "message": "Unauthorized user"
}

