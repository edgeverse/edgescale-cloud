# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import namedtuple

AccountTypes = namedtuple('AccountTypes', ['id', 'name'])
Account = namedtuple('Account', ['id', 'first_name', 'last_name', 'company_name',
                                 'telephone', 'email', 'job_title', 'account_type',
                                 'created_at', 'status'])
AccountShort = namedtuple('AccountShort', ['id', 'email', 'type_id'])

User = namedtuple('User', ['uid', 'username', 'password', 'salt', 'admin', 'account_type_id', 'status'])
UserInfo = namedtuple('UserInfo', ['uid', 'username', 'email'])
UserPutObj = namedtuple('User', ['id', 'username'])
UserAll = namedtuple('User', ['id', 'username', 'email', 'display_name', 'admin',
                              'created_at', 'updated_at', 'timezone', 'image', 'status'])

LimitType = namedtuple('LimitType', ['id', 'name', 'desc', 'default_max_limit', 'default_max_sec', 'is_per_time'])
Limit = namedtuple('Limit', ['limit_type_id', 'limit_type', 'max_limit', 'max_sec'])

SolutionRoleInfo = namedtuple('SolutionRoleInfo', ['solution_id', 'user_id', 'is_public'])

Certificate = namedtuple('Certificate', ['body', 'private_key', 'chain'])

VendorItem = namedtuple('VendorItem', ['id', 'name'])
