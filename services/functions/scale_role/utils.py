# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from model.models import DccaRole, DccaPermission

actions = ['get', 'post', 'put', 'delete']


class DCCAException(Exception):
    pass


class InvalidInputException(Exception):
    pass


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


def role_name_taken(name):
    if DccaRole.exists(name):
        raise InvalidInputException('The role name has been taken')


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


def action_validate(action):
    if action.lower() not in actions:
        raise InvalidInputException('The action should be valid, only allow {}'.format(','.join(actions)))


def duplicate_name(name):
    if DccaPermission.exists(name):
        raise InvalidInputException('Duplicate name')

