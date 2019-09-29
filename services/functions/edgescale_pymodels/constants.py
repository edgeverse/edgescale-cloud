# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os

# ### Task status defination START
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

TASK_STATUS_NAMES = {
    TASK_STATUS_READY: 'Created',
    TASK_STATUS_SCHEDULED: 'Scheduled',
    TASK_STATUS_CANCELED: 'Canceled',
    TASK_STATUS_FAIL: 'Fail',
    TASK_STATUS_STARTED: 'Started',
    TASK_STATUS_COMPLETE: 'Complete',
    TASK_STATUS_START_FAIL: 'StartFail',
}

TASK_STATUS_FILTER = {
    TASK_STATUS_READY_MSG: TASK_STATUS_READY,
    TASK_STATUS_SCHEDULED_MSG: TASK_STATUS_SCHEDULED,
    TASK_STATUS_COMPLETE_MSG: TASK_STATUS_COMPLETE,
}

_task_status = list(TASK_STATUS_NAMES.keys())
_task_status.extend(list(map(str, list(_task_status))))
TASK_STATUS = tuple(_task_status)
# ### Task status defination END


# DA task status
DA_TASK_STATUS_UNKNOWN = -1
DA_TASK_STATUS_READY = 0
DA_TASK_STATUS_PENDING = 1
DA_TASK_STATUS_CREATING = 2
DA_TASK_STATUS_STARTING = 3
DA_TASK_STATUS_FAILED = 4
DA_TASK_STATUS_RUNNING = 5
DA_TASK_STATUS_DELETING = 6
DA_TASK_STATUS_DELETED = 7
DA_TASK_STATUS_TIMEOUT = 8
DA_TASK_STATUS_ERROR = 9
DA_TASK_STATUS_K8S_NO_RESPONSE = 10
DA_TASK_STATUS_START_FAIL = 11
DA_TASK_STATUS_INPUT_ERROR = 12
DA_TASK_STATUS_APP_NOT_FOUND = 13

DA_TASK_SCHEDULED = [DA_TASK_STATUS_READY, DA_TASK_STATUS_PENDING, DA_TASK_STATUS_CREATING,
                     DA_TASK_STATUS_STARTING, DA_TASK_STATUS_RUNNING, DA_TASK_STATUS_DELETING]
DA_TASK_COMPLETE = [DA_TASK_STATUS_DELETED]
DA_TASK_FAIL = [DA_TASK_STATUS_FAILED, DA_TASK_STATUS_TIMEOUT,
                DA_TASK_STATUS_ERROR, DA_TASK_STATUS_K8S_NO_RESPONSE,
                DA_TASK_STATUS_START_FAIL, DA_TASK_STATUS_INPUT_ERROR,
                DA_TASK_STATUS_APP_NOT_FOUND]

DA_TASK_STATUS_FAILED_MSG = 'Failed'
DA_TASK_STATUS_NAMES = {
    DA_TASK_STATUS_UNKNOWN: 'Unknown',
    DA_TASK_STATUS_READY: 'Ready',
    DA_TASK_STATUS_PENDING: 'Running',
    DA_TASK_STATUS_CREATING: 'Creating',
    DA_TASK_STATUS_STARTING: 'Starting',
    DA_TASK_STATUS_FAILED: DA_TASK_STATUS_FAILED_MSG,
    DA_TASK_STATUS_RUNNING: 'Running',
    DA_TASK_STATUS_DELETING: 'Deleting',
    DA_TASK_STATUS_DELETED: 'Deleted',
    DA_TASK_STATUS_TIMEOUT: 'Timeout',
    DA_TASK_STATUS_ERROR: 'Error',
    DA_TASK_STATUS_K8S_NO_RESPONSE: 'StartFailure',
    DA_TASK_STATUS_INPUT_ERROR: 'InvalidParameter',
    DA_TASK_STATUS_APP_NOT_FOUND: 'AppNotFound',
}

DA_TASK_STATUS_NAMES_SHOWN = {
    DA_TASK_STATUS_READY: 'Ready',
    DA_TASK_STATUS_PENDING: 'Pending',
    DA_TASK_STATUS_CREATING: 'Creating',
    DA_TASK_STATUS_STARTING: 'Starting',
    DA_TASK_STATUS_FAILED: DA_TASK_STATUS_FAILED_MSG,
    DA_TASK_STATUS_RUNNING: 'Running',
    DA_TASK_STATUS_DELETING: 'Deleting',
    DA_TASK_STATUS_DELETED: 'Deleted'
}

COMMON_TASK_STATUS = {
    TASK_STATUS_READY: 'Ready',          # 0
    TASK_STATUS_SCHEDULED: 'Running',    # 1
    TASK_STATUS_COMPLETE: 'Done',        # 5
    TASK_STATUS_FAIL: 'Failed'           # 3
}
da_task_status = list(DA_TASK_STATUS_NAMES.keys())
da_task_status.extend(list(map(str, list(da_task_status))))
DA_TASK_STATUS = tuple(da_task_status)
# ### DA task status END


# ### OTA task codes START
OTA_TASK_CODE_UNKNOWN = -1
OTA_TASK_CODE_START = 0
OTA_TASK_CODE_FETCH = 1
OTA_TASK_CODE_VERIFY = 2
OTA_TASK_CODE_INSTALL = 3
OTA_TASK_CODE_REBOOT = 4
OTA_TASK_CODE_ROLLBACK = 5
OTA_TASK_CODE_COMPLETE = 6
OTA_TASK_CODE_DONE = 7

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

_ota_task_status = list(OTA_STATUS_NAMES.keys())
OTA_TASK_STATUS = tuple(_ota_task_status)
# ### OTA task codes END


TASK_TYPE_APP = 0
TASK_TYPE_SOLUTION = 1
TASK_TYPE_NAMES = {
    TASK_TYPE_APP: 'deploy_app',
    TASK_TYPE_SOLUTION: 'deploy_solution'
}

LIMIT = 2000
OFFSET = 0

TIMEOUT_DAYS = 1

RESOURCE_DEPLOY_APP = 'https://{dns}:{port}/v1/user/{uid}/app'
RESOURCE_GET_APPSUM = 'https://{dns}:{port}/v1/user/{uid}/appsum'
RESOURCE_POST_TASK = 'https://{dns}:{port}/v2/user/{uid}/task'
RESOURCE_QUERY_APP_STATUS = 'https://{dns}:{port}/v1/user/{uid}/app/{name}'

_dirname = os.path.dirname(os.path.realpath(__file__))
CERTS = (
    os.path.join(_dirname, 'keys', 'admin.pem'),
    os.path.join(_dirname, 'keys', 'admin-key.pem'),
)

HEADERS = {
    'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}

env = 'dev'
IMAGE_BUCKET = 'dcca-images'
USER_TOKEN_KEY = 'x^0&*${<?@[l#~?+'
MAIL_TOKEN_KEY = 'z{<?@[l#~?+{<[U+'
TIME_FORMAT_STR = '%Y-%m-%d|%H:%M'
DEFAULT_MAIL_TOKEN_TIMEOUT = 1440
DEFAULT_MAIL_TOKEN_TIMEOUT_STR = 'one day'

STORAGE_PREFIX = 'https://storage.edgescale.org/'

LIMIT_TYPE_ID_CREATE_SOLUTION = 6


EMPTY_PORTS_MAPPING = [{"containerPort": '', "hostPort": ""}]
EMPTY_VOLUMES_MAPPING = [{"hostPath": {"path": ""}, "name": ""}]
EMPTY_VOLUME_MOUNTS_MAPPING = [{"readOnly": False, "mountPath": "", "name": ""}]

IMAGE_ROOT = 'https://s3-us-west-2.amazonaws.com/dcca-images'
BUCKET = 'dcca-images'

GROUP_CATEGORY_DEVICE = 'device'

GROUP_NAME_EMPTY_MSG = 'The parameter "name" cannot be empty.'

DEFAULT_MODEL_GROUP_LIMTI = 10
DEFAULT_GROUP_LIMTI = 20
DEFAULT_GROUP_OFFSET = 0

DEFAULT_GROUP_LIMTI_STATISTICS = 50

DEFAULT_GROUP_STATISTICS = 1000

DEFAULT_MAX_GROUP_LIMTI = 10

DA_TASK_STATUS_READY = 0

TASK_TYPE_DEPLOY_APP = 0
TASK_TYPE_DEPLOY_SOLUTION = 1
TASK_STATUS_READY = 0

OTA_TASK_CODE_START = 0

TASK_TYPE_APP = 0
TASK_TYPE_SOLUTION = 1

ADMIN_FLAG = 1
DEFAULT_ROLE_ID = 1
DEFAULT_LIMIT = 10
DEFAULT_OFFSET = 0

ACCOUNT_TYPE_COMMON_USER_ID = 4
ACCOUNT_TYPE_OXM_ID = [2, 3]

ACTIVE = True
INACTIVE = False

REQUEST_STATUS_CODE_PENDING = 0
REQUEST_STATUS_CODE_APPROVED = 1
REQUEST_STATUS_CODE_REJECTED = 2
REQUEST_STATUS_PENDING = 'Pending'
REQUEST_STATUS_APPROVED = 'Approved'
REQUEST_STATUS_REJECTED = 'Rejected'

REQUEST_STATUS = {
    REQUEST_STATUS_CODE_PENDING: REQUEST_STATUS_PENDING,
    REQUEST_STATUS_CODE_APPROVED: REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_CODE_REJECTED: REQUEST_STATUS_REJECTED
}

MSG_CANNOT_QUERY_DETAIL = 'Only administrator can query user\' information.'

ACTION_APPROVE = 'approve'
ACTION_REJECT = 'reject'

TYPE_OEM = 2
TYPE_USER = 4

filter_type_convert = {
    "oem": TYPE_OEM,
    "user": TYPE_USER
}

filter_status_convert = {
    "approve": REQUEST_STATUS_CODE_APPROVED,
    "reject": REQUEST_STATUS_CODE_REJECTED,
    "pending": REQUEST_STATUS_CODE_PENDING
}

subject_html_user = 'Your request has been approved'
body_html_user = '''
<html>
<head></head>
<body>
  <p>Your account has been created: </p>
  <h4>{account}</h4>
  <p>Here's your password: </p>
  <h4>{password}</h4>
</body>
</html>
'''

body_html_oem = '''
<html>
<head></head>
<body>
  <p>Your account has been created: </p>
  <h4>{account}</h4>
  <p>Here's your password: </p>
  <h4>{password}</h4>
  <p>Here's your oem_id: </p>
  <h4>{oem_id}</h4>
  <p>Please keep it safe for later use.</p>
</body>
</html>
'''

subject_html_user_reject = 'Dear customer'
body_html_user_reject = '''
<html>
<head></head>
<body>
  <p>Sorry. Your request has been rejected.</p>
</body>
</html>
'''

subject_html_marketing = "The user's account has been created"
body_html_marketing = '''
<html>
<head></head>
<body>
  <p>An email has been sent to the user({email}).</p>
</body>
</html>
'''

NOT_ADMIN_CANNOT_CREATE_MSG = 'Only administrator can create vendor'
VENDOR_ALREADY_EXIST_MSG = 'Vendor already exist'

UNAUTH_RESULT = {
    "error": True,
    "status": "fail",
    "message": "Unauthorized user"
}

body_html_rest_password =  """<html>
    <head></head>
    <body>
      <h1>Reset your password</h1>
      Your account has been created <h4>{account}</h4>
      <p>Click the link below to
         <a href='{host}/password?token={token}'>Reset</a>
         your password in {time}.
      </p>
    </body>
    </html>"""

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
