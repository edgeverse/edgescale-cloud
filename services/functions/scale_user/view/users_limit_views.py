# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

#! -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify

from utils import *
from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pymodels.nametuples import Limit, LimitType
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import check_json


users_limit_bp = Blueprint("users_limit", __name__)


@users_limit_bp.route("/limits", methods=["GET"])
def query_user_limits_by_uid():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') if request.args.get('limit') else 20
    offset = request.args.get('offset') if request.args.get('offset') else 0

    request.cursor.execute(query_user_limit_by_uid_sql, (uid, limit, offset))
    limit_info = request.cursor.fetchall()

    results = {
        'limits': [],
        'size': 0
    }

    for _limit in limit_info:
        limit = Limit._make(_limit)
        results['limits'].append(limit._asdict())

    results['size'] = len(results['limits'])
    return jsonify(results)


@users_limit_bp.route("/limits", methods=["PUT"])
def modify_user_limits():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False

    if not is_admin:
        return jsonify({
            'statis': 'fail',
            'message': 'Only administrator can access this.'
        })

    check_json(request)
    username = get_json(request).get('username')
    limit_type_id = get_json(request).get('limit_type_id')
    max_limits = get_json(request).get('max_limit')
    max_second = get_json(request).get('max_seconds')

    if not max_limits:
        return jsonify({
            'status': 'fail',
            'message': 'The "max_limits" cannot be empty.'
        })

    is_user_exist, user_id = user_exist(request.cursor, username)
    if not is_user_exist:
        return jsonify({
            'status': 'fail',
            'message': 'Incorrect username, user not exist'
        })

    limit_type = query_limit_type(request.cursor, limit_type_id)

    if limit_type.default_max_sec is None:
        if max_second:
            return jsonify({
                'status': 'fail',
                'message': 'Max seconds must be empty for this limit type.'
            })
        else:
            max_second = None
    else:
        if not max_second:
            return jsonify({
                'status': 'fail',
                'message': 'Max seconds cannot be empty for this limit type.'
            })

    try:
        request.cursor.execute(update_user_limit_sql, (max_limits, max_second, user_id, limit_type_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to update limit data')

    return jsonify({
        'status': 'success',
        'message': 'Success to update the max limit data for user'
    })


@users_limit_bp.route("/limits/types", methods=["GET"])
def query_limit_types():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False

    if not is_admin:
        return jsonify({
            'statis': 'fail',
            'message': 'Only administrator can access this.'
        })

    request.cursor.execute(query_all_types_sql)
    limit_types = request.cursor.fetchall()

    results = []
    for _type in limit_types:
        _t = LimitType._make(_type)
        results.append(_t._asdict())

    return jsonify({
        'types': results,
        'size': len(results)
    })
