# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import namedtuple


TaskTemlt = namedtuple('Task', ['id', 'name', 'desc', "owner_id", 'created_at', 'updated_at', 'body'])
TaskTemltShort = namedtuple('Task', ['id', 'name', 'desc', 'created_at', 'updated_at'])

Device = namedtuple('Device', ['id', 'name', 'display_name', 'model', 'type', 'platform', 'vendor'])
App = namedtuple('App', ['id', 'name', 'display_name', 'username', 'image', 'description'])


TASK_TYPE_APP = 0
TASK_TYPE_SOLUTION = 1
TASK_TYPE_REBOOT = 2
TASK_TYPE_RESET = 3
TASK_TYPE_COMMON = 5
TASK_TYPE_NAMES = {
    TASK_TYPE_APP: 'deploy_app',
    TASK_TYPE_SOLUTION: 'deploy_solution',
    TASK_TYPE_REBOOT: 'device_reboot',
    TASK_TYPE_RESET: 'device_factory_reset',
    TASK_TYPE_COMMON: 'common_task'
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

TASK_STATUS_READY_MSG = 'Created'
TASK_STATUS_SCHEDULED_MSG = 'Scheduled'
TASK_STATUS_COMPLETE_MSG = 'Complete'

TASK_STATUS_HEALTHY = [TASK_STATUS_READY, TASK_STATUS_SCHEDULED, TASK_STATUS_STARTED]
TASK_STATUS_NAMES = {
    TASK_STATUS_READY: TASK_STATUS_READY_MSG,
    TASK_STATUS_SCHEDULED: TASK_STATUS_SCHEDULED_MSG,
    TASK_STATUS_CANCELED: 'Canceled',
    TASK_STATUS_FAIL: 'Fail',
    TASK_STATUS_STARTED: 'Started',
    TASK_STATUS_COMPLETE: TASK_STATUS_COMPLETE_MSG,
    TASK_STATUS_START_FAIL: 'StartFail',
}

TASK_STATUS_FILTER = {
    TASK_STATUS_READY_MSG: TASK_STATUS_READY,
    TASK_STATUS_SCHEDULED_MSG: TASK_STATUS_SCHEDULED,
    TASK_STATUS_COMPLETE_MSG: TASK_STATUS_COMPLETE,
}

RESOURCE_POST_TASK = 'https://{dns}:{port}/v2/user/{uid}/task'
IMAGE_ROOT = 'https://s3-us-west-2.amazonaws.com/dcca-images'

UNAUTH_RESULT = {
    "error": True,
    "status": "fail",
    "message": "Unauthorized user"
}
