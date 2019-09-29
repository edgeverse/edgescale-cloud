# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.view_utils import get_oemid
from model.constants import User
from model.raw_sqls import *

permission_bp = Blueprint("permission", __name__)


@permission_bp.route("", methods=["GET"])
def query_user_perms():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    request.cursor.execute(query_user_perm_sql, (uid,))

    user = request.cursor.fetchone()
    user = User._make(user)

    result = user._asdict()
    result['account_type'] = {
        'id': result['account_type_id'],
        'name': result['account_type_name']
    }
    del result['account_type_id']
    del result['account_type_name']

    return jsonify(result)
