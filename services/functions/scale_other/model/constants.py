# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
from collections import namedtuple

DATE_TIME_FORMAT = '%Y-%m-%d %H'
DATE_TIME_DAY_FORMAT = '%Y-%m-%d'
DATE_FORMAT_LONG = '%Y-%m-%d'
DATE_FORMAT_SHORT = '%Y%m%d'
DATETIME_FORMAT = '%Y%m%d'

HARBOR_API = 'https://registry.edgescale.org/api'

_dirname = os.path.dirname(os.path.realpath(__file__))
certs = (
    os.path.join(os.path.dirname(_dirname), 'admin.pem'),
    os.path.join(os.path.dirname(_dirname), 'admin-key.pem'),
)

LIMIT_TYPE_DEPLOY_ID = 2
LIMIT_TYPE_MODEL = 5

REDIS_KEY_DEPLOY_FORMAT = '{rest_api_id}:{user_id}:{datetime}:da'
CACHE_KEY_API_USAGE = '{rest_api_id}:{user_id}:{date_id}'
CACHE_KEY_CREATE_DEVICE = '{rest_api_id}:{user_id}:{date_id}:cd'

ShortDevice = namedtuple('Device', ['id', 'name', 'display_name'])
InfoModel = namedtuple("Model", ['id', 'model', 'type', 'platform', 'vendor', 'is_public'])
Solution = namedtuple("Solution", ['id', 'solution', 'model', 'type', 'platform', 'vendor', 'version', 'image', 'link', 'is_public'])
Position = namedtuple("Position", ['id', 'latitude', 'longitude', 'ip_address', 'name'])
Application = namedtuple("Application", ['id', 'name', 'display_name', 'description', 'likes', 'stars', 'created_at', 'is_public', 'in_store'])
ModelInfo = namedtuple('Model', ['id', 'model', 'type', 'platform', 'vendor', 'is_public', 'owner_id'])
SimpleService = namedtuple('SimpleService', ['id', 'uuid'])
Service = namedtuple('Service', ['uuid', 'name', 'protocal', 'cipher_suite',
                                 'server_certificate_format', 'server_certificate_key',
                                 'connection_url', 'config',
                                 'signing_certificate_format', 'signing_certificate_key'])
RegistryShort = namedtuple('RegistryShort', ['id', 'name', 'public', 'desc', 'created_at'])
RegistryFull = namedtuple('RegistryFull', ['id', 'name', 'public', 'desc', 'owner_id'])
CommonService = namedtuple('CommonService', ['id', 'name', 'url', 'port', 'access_token'])
AppInstance = namedtuple('AppInstance', ['id', 'name', 'registry', 'image', 'commands', 'args', 'hostnetwork',
                                         'ports', 'volumes', 'volumeMounts', 'cap_add', 'morepara', 'app_name'])
Model = namedtuple('Model', ['id', 'model', 'type', 'platform', 'vendor', 'is_public', 'owner_id'])
Audits = namedtuple('Audits', ['id', 'approved', 'comment', 'username', 'created_at', 'status', 'type'])
AuditsShort = namedtuple('AuditsShort', ['id', 'approved', 'approve_item', 'to_public', 'status'])

bucket_list = {
    "solution": "edgescale.solutions",
    "app": "dcca-images",
    "eiq": "eiq-cloud"
}

RESOURCE_GET_STATUS = 'https://{dns}:{port}/v1/user/{uid}/app'
RESOURCE_DEPLOY_APP = 'https://{dns}:{port}/v1/user/{uid}/app'
RESOURCE_DELETE_APP_V2 = 'https://{dns}:{port}/v1/user/{uid}/app/{app_name}'
RESOURCE_GET_APP_CONLOG = 'https://{dns}:{port}/v1/user/{uid}/app/{app_name}/log'
RESOURCE_GET_APP_EVENT = 'https://{dns}:{port}/v1/user/{uid}/app/{app_name}/event'
RESOURCE_POST_APP_REBOOT = 'https://{dns}:{port}/v1/user/{uid}/app/{app_name}/reboot'

# The app install per-second
LIMIT_TYPE_ID_MAX_PER_SEC_INSTALL = 3
DEPLOY_APP_KEY_INSTALL = 'd:i:{}'

# The app uninstall per-second
LIMIT_TYPE_ID_MAX_PER_SEC_UNINSTALL = 4
DEPLOY_APP_KEY_UNINSTALL = 'd:u:{}'

# The template for container
container_template = '''
{
   "apiVersion":"v1",
   "kind":"Pod",
   "metadata":{
      "name": "<app_name>",
      "labels": {
         "name": "<app_name>"
      }
   },
   "spec":{
      "hostNetwork": true,
      "containers": [
         {
            "name":"<app_name>",
            "image":"<docker_repo/app_name:version>",
            "imagePullPolicy":"IfNotPresent",
            "securityContext": {
               "privileged":true
            }
         }
      ],
      "nodeSelector": {
         "kubernetes.io/hostname": "<device_id>"
      },
      "imagePullSecrets": [
          {
              "name": "secret"
          }
      ]
   }
}
'''
