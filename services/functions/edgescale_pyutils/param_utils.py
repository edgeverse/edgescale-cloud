# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import re

from edgescale_pyutils.boto3_utils import s3_folder_exists, create_foler
from edgescale_pyutils.exception_utils import InvalidInputException, InvalidParameterException, DCCAException, \
    EdgeScaleException


def check_username(username):
    if not username:
        return {
            'status': 'fail',
            'message': 'Invalid username, cannot be empty'
        }
    elif len(username) <= 4 or len(username) > 255:
        return {
            'status': 'fail',
            'message': 'The length of username is at least 4'
        }
    elif ' ' in username:
        return {
            'status': 'fail',
            'message': 'Invalid username cannot contain whitespace'
        }
    elif username.isdigit():
        return {
            'status': 'fail',
            'message': 'Username cannot be all digit'
        }
    elif re.match(r'^\d.*', username):
        return {
            'status': 'fail',
            'message': 'Username cannot start with digit'
        }

    return None


def check_email(email):
    if not email:
        return {
            'error': True,
            'status': 'fail',
            'message': 'Email cannot be empty'
        }
    elif ' ' in email:
        return {
            'error': True,
            'status': 'fail',
            'message': 'Invalid email, cannot contain whitespace'
        }
    elif not re.match(r'(^[\w-]+(\.[\w-]+)*@[\w-]+(\.[\w-]+)+$)', email):
        return {
            'error': True,
            'status': 'fail',
            'message': 'Invalid email pattern'
        }

    return None


def empty_check(value, error_message):
    if not value:
        raise InvalidInputException(error_message)


def empty_check_chian(value, error_message, errors=None):
    if errors is None:
        errors = []

    if not value:
        errors.append(error_message)
    return errors


def check_if_not_exist(username):
    if not s3_folder_exists(username):
        create_foler(username)
        return True
    else:
        return False


def input_valid_check(value, error_message):
    if not value or not re.match(r'^[A-Za-z0-9_-]*$', value):
        raise InvalidInputException(error_message)


def _empty_validate(value, message):
    if not value:
        raise InvalidInputException(message)


def _not_exist_validate(value, message):
    if not value:
        raise InvalidInputException(message)


def _exist_validate(value, message):
    if value:
        raise InvalidInputException(message)


def contain_whitespace(name):
    if ' ' in name:
        raise InvalidInputException('Can not contain whitespace.')


def role_id_empty(role_id):
    _empty_validate(role_id, "Role ID cannot be empty.")


def role_name_empty(name):
    if not name:
        raise InvalidInputException('Role name cannot be empty.')


def role_not_exist(role):
    _not_exist_validate(role, message='Role not exist.')


def user_id_empty(user_id):
    _empty_validate(user_id, "User ID cannot be empty.")


def user_not_exist(user):
    _not_exist_validate(user, message='User not exist.')


def resource_id_empty(perm_id):
    _empty_validate(perm_id, message='Resource ID cannot be empty.')


def resource_not_exist(perm):
    _not_exist_validate(perm, message='Resource not exist')


actions = ['get', 'post', 'put', 'delete']


def action_validate(action):
    if action.lower() not in actions:
        raise InvalidInputException('The action should be valid, only allow {}'.format(','.join(actions)))


def validate_resource(resource):
    limits = {}
    if not resource:
        return
    try:
        if 'cpu' in resource:
            float(resource['cpu'])
            limits['cpu'] = resource['cpu']
    except Exception:
        raise InvalidParameterException('cpu should be float')

    try:
        if 'memory' in resource:
            if 'M' in resource['memory']:
                resource['memory'] = resource['memory']\
                    .split('M')[0].split('G')[0]
            int(resource['memory'])
            # resource unit is MiByte
            limits['memory'] = resource['memory']
    except Exception:
        raise InvalidParameterException('memory should be int')

    return limits


def validate_envrionment(env):
    ret = []
    if env and isinstance(env, list):
        for e in env:
            if 'name' in e and "value" in e:
                if e["name"].strip() != "":
                    ret.append({"name": e["name"], "value": e["value"]})
            else:
                raise InvalidParameterException('env should use keys name and value')
    return ret


def check_permission(permission):
    if permission not in ['private', 'public']:
        raise DCCAException("invalid permission type")

    if permission == 'public':
        return True
    else:
        return False


def check_tag_name(tag_name):
    if not tag_name:
        raise EdgeScaleException('Tag cannot be empty')
    else:
        return None


def check_json(request):
    try:
        request.json
    except Exception as e:
        raise InvalidInputException("Please check your request, " + str(e))
