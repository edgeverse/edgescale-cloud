# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import namedtuple

User = namedtuple('User', ['username', 'email', 'is_admin', 'display_name', 'account_type_id', 'account_type_name'])
