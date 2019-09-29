# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import OrderedDict

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.view_utils import get_oemid
from model.constants import *
from model.raw_sqls import *

info_bp = Blueprint("info", __name__)


@info_bp.route("/application", methods=["GET"])
def query_user_applications():
    _, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    uid = request.args.get('uid')
    limit = request.args.get('limit') if request.args.get('limit') else 10
    offset = request.args.get('offset') if request.args.get('offset') else 0
    order_by = request.args.get('order_by')
    order_type = request.args.get('order_type')
    filter_text = request.args.get('filter_text')
    filt_limit = " LIMIT {} OFFSET {};".format(limit, offset)
    filt = ''
    filt_txt = ''

    if filter_text:
        filt = filt_txt = " AND (name LIKE '%{}%' OR display_name LIKE '%{}%') ".format(filter_text, filter_text)
    if order_by:
        filt += "ORDER BY {} {} ".format(order_by, order_type)

    query_user_applications_cmd = query_user_applications_sql.format(uid=uid) + filt + filt_limit
    count_applications_cmd = count_applications_sql.format(uid=uid) + filt_txt

    request.cursor.execute(query_user_applications_cmd)
    apps = request.cursor.fetchall()

    request.cursor.execute(count_applications_cmd)
    total = request.cursor.fetchone()[0]

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = total

    app_all = []
    for app in apps:
        _app = Application._make(app)._asdict()
        _app['created_at'] = _app['created_at'].strftime("%Y-%m-%d:%H:%M:%S")
        app_all.append(_app)

    results['list'] = app_all
    return jsonify(results)


@info_bp.route("/model", methods=["GET"])
def query_user_models():
    _, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    uid = request.args.get('uid')
    limit = request.args.get('limit') if request.args.get('limit') else 10
    offset = request.args.get('offset') if request.args.get('offset') else 0
    filter_text = request.args.get('filter_text')
    filt_limit = " LIMIT {} OFFSET {};".format(limit, offset)
    filt = ''

    if filter_text:
        filt = "AND (model LIKE '%{}%' OR type LIKE '%{}%')".format(filter_text, filter_text)

    query_user_models_cmd = query_user_models_sql.format(user_id=uid) + filt + filt_limit
    count_models_cmd = count_models_sql.format(uid=uid) + filt

    request.cursor.execute(query_user_models_cmd)
    models = request.cursor.fetchall()

    request.cursor.execute(count_models_cmd)
    total = request.cursor.fetchone()[0]

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = total

    model_all = []
    for model in models:
        _model = InfoModel._make(model)._asdict()
        model_all.append(_model)

    results['list'] = model_all
    return jsonify(results)


@info_bp.route("/position", methods=["GET"])
def query_user_device_position():
    _, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    uid = request.args.get('uid')
    query_user_device_pos_cmd = query_user_device_pos_sql.format(uid=uid)
    query_device_pos_count_cmd = query_device_pos_count_sql.format(uid=uid)

    request.cursor.execute(query_device_pos_count_cmd)
    counts = request.cursor.fetchall()

    request.cursor.execute(query_user_device_pos_cmd)
    positions = request.cursor.fetchall()

    results = OrderedDict()

    results['area'] = []
    for count in counts:
        _count = OrderedDict()
        _count[count[0]] = count[1]
        results['area'].append(_count)

    position_all = []
    for pos in positions:
        _pos = Position._make(pos)._asdict()
        position_all.append(_pos)

    results['list'] = position_all
    return jsonify(results)


@info_bp.route("/solution", methods=["GET"])
def query_user_solutions():
    _, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    uid = request.args.get('uid')
    limit = request.args.get('limit') if request.args.get('limit') else 10
    offset = request.args.get('offset') if request.args.get('offset') else 0
    filter_text = request.args.get('filter_text')
    filt_limit = " LIMIT {} OFFSET {};".format(limit, offset)
    filt = ''

    if filter_text:
        filt = " AND (solution LIKE '%{}%' OR image LIKE '%{}%')".format(filter_text, filter_text)

    query_user_solutions_cmd = query_user_solutions_sql.format(uid=uid) + filt + filt_limit
    count_solutions_cmd = count_solutions_sql.format(uid=uid) + filt

    request.cursor.execute(query_user_solutions_cmd)
    solutions = request.cursor.fetchall()

    request.cursor.execute(count_solutions_cmd)
    total = request.cursor.fetchone()[0]

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = total

    solution_all = []
    for solution in solutions:
        _solution = Solution._make(solution)._asdict()
        solution_all.append(_solution)

    results['list'] = solution_all
    return jsonify(results)
