# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import namedtuple


Device = namedtuple('Device', ['id', 'name', 'created_at', 'local_ip', 'model', 'type', 'platform', 'vendor', 'display_name'])
DeviceTag = namedtuple('DeviceTag', ['device_id', 'tag_id', 'tag_name'])
DeviceLocation = namedtuple('DeviceLocation', ['id', 'name', 'location', 'display_name'])
Position = namedtuple('Position', ['device_id', 'lat', 'lng'])
DeviceInfo = namedtuple('DeviceInfo', ['id', 'name', 'certname', 'created_at', 'updated_at', 'last_report',
                                       'display_name', 'solution', 'version'])
DeviceOnlineInfo = namedtuple('DeviceOnlineInfo', ['name', 'online'])
Device_Msg = namedtuple('Device_Msg', ['device_owner_id', 'model_id', 'model_permission', 'model_owner_id', 'model_default_solution_id'])
ShortDevice = namedtuple('Device', ['id', 'name'])
Tag = namedtuple('Tag', ['id', 'name'])
Device_Model = namedtuple('Device_Model', ['device_id', 'model', 'type', 'platform', 'vendor'])
OEM = namedtuple('OEM', ['user_id', 'chain'])
EndPoint = namedtuple('EndPoint', ['name', 'url', 'port', 'access_token'])
LocationItem = namedtuple('LocationItem', ['device_id', 'name', 'continent', 'short', 'status'])
LocationItem_v2 = namedtuple('LocationItem', ['device_id', 'name', 'online', 'continent_id'])

LIMIT_TYPE_DEVICE = 1       # Maximum number that user can create device
LIMIT_TYPE_CAN_BIND = 5     # Maximum device that user can bind to model

NO_MAX_LIMIT = 0


CREATED = 1
NEW = 2
AUTHENTICATED = 3
ACTIVE = 4
INACTIVE = 5
RETIRED = 6

DEVICE_STATUS = {
    'created': 1,
    'new': 2,
    'authenticated': 3,
    'active': 4,
    'inactive': 5,
    'retired': 6
}

TYPE_COUNTRY = 'location'
TYPE_PLATFORM = 'platform'


DEFAULT_GROUP_LIMTI = 20
DEFAULT_GROUP_OFFSET = 0

DEFAULT_GROUP_LIMTI_STATISTICS = 50

TASK_TYPE_APP = 0
TASK_TYPE_SOLUTION = 1

TASK_TYPE_NAMES = {
    TASK_TYPE_APP: 'deploy_app',
    TASK_TYPE_SOLUTION: 'deploy_solution'
}

OTA_TASK_CODE_UNKNOWN = -1
OTA_TASK_CODE_START = 0
OTA_TASK_CODE_FETCH = 1
OTA_TASK_CODE_VERIFY = 2
OTA_TASK_CODE_INSTALL = 3
OTA_TASK_CODE_REBOOT = 4
OTA_TASK_CODE_ROLLBACK = 5
OTA_TASK_CODE_COMPLETE = 6

OTA_TASK_STATUS_UNKNOWN = 'Unknown'
OTA_TASK_STATUS_START = 'ota-start'
OTA_TASK_STATUS_FETCH = 'ota-fetch'
OTA_TASK_STATUS_VERIFY = 'ota-verify'
OTA_TASK_STATUS_INSTALL = 'ota-install'
OTA_TASK_STATUS_REBOOT = 'ota-reboot'
OTA_TASK_STATUS_ROLLBACK = 'ota-rollback'
OTA_TASK_STATUS_COMPLETE = 'ota-complete'

TASK_STARTED_OTA_STATUS = [
    OTA_TASK_CODE_START,
    OTA_TASK_CODE_FETCH,
    OTA_TASK_CODE_VERIFY,
    OTA_TASK_CODE_INSTALL,
    OTA_TASK_CODE_REBOOT,
    OTA_TASK_CODE_ROLLBACK
]

TASK_COMPLETE_OTA_STATUS = [OTA_TASK_CODE_COMPLETE]

OTA_STATUS_NAMES = {
    # OTA_TASK_STATUS_UNKNOWN: OTA_TASK_CODE_UNKNOWN,
    OTA_TASK_STATUS_START: OTA_TASK_CODE_START,
    OTA_TASK_STATUS_FETCH: OTA_TASK_CODE_FETCH,
    OTA_TASK_STATUS_VERIFY: OTA_TASK_CODE_VERIFY,
    OTA_TASK_STATUS_INSTALL: OTA_TASK_CODE_INSTALL,
    OTA_TASK_STATUS_REBOOT: OTA_TASK_CODE_REBOOT,
    OTA_TASK_STATUS_ROLLBACK: OTA_TASK_CODE_ROLLBACK,
    OTA_TASK_STATUS_COMPLETE: OTA_TASK_CODE_COMPLETE,
}

OTA_STATUS_MAP = {
    # OTA_TASK_CODE_UNKNOWN: OTA_TASK_STATUS_UNKNOWN,
    OTA_TASK_CODE_START: OTA_TASK_STATUS_START,
    OTA_TASK_CODE_FETCH: OTA_TASK_STATUS_FETCH,
    OTA_TASK_CODE_VERIFY: OTA_TASK_STATUS_VERIFY,
    OTA_TASK_CODE_INSTALL: OTA_TASK_STATUS_INSTALL,
    OTA_TASK_CODE_REBOOT: OTA_TASK_STATUS_REBOOT,
    OTA_TASK_CODE_ROLLBACK: OTA_TASK_STATUS_ROLLBACK,
    OTA_TASK_CODE_COMPLETE: OTA_TASK_STATUS_COMPLETE,
}

# Task status defination START
TASK_STATUS_UNKNOWN = -1
TASK_STATUS_READY = 0
TASK_STATUS_SCHEDULED = 1
TASK_STATUS_CANCELED = 2
TASK_STATUS_FAIL = 3
TASK_STATUS_STARTED = 4
TASK_STATUS_COMPLETE = 5
TASK_STATUS_START_FAIL = 6

# 1	Asia	AS
# 2	Africa	AF
# 3	Europe	EU
# 4	South America	SA
# 5	North America	NA
# 6	Oceania	OA
# 7	Antarctica	AN

CONTINENTS = {
    1: ('Asia', 'AS'),
    2: ('Africa', 'AF'),
    3: ('Europe', 'EU'),
    4: ('South America', 'SA'),
    5: ('North America', 'NA'),
    6: ('Oceania', 'OA'),
    7: ('Antarctica', 'AN'),
}

def_endpoints = {
    "api": {"uri": ""},
    "mqtt": {"uri": ""},
    "docker_trust_token": "YWRtaW46SGFyYm9yMTIzNDU=",
    "docker_content_trust_server": "",
    "oem_trust_ca": "",
    "accesskey": "access_key0"
}

status_list = ["created", "new", "auth", "active", "inactive", "retired"]
