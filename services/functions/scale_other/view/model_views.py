# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.view_utils import get_oemid, get_json
from model import IS_DEBUG
from model.constants import *
from edgescale_pyutils.param_utils import check_json
from utils import *

model_bp = Blueprint("model", __name__)


@model_bp.route("", methods=["GET"])
def query_models():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    my_model = request.args.get('my_model') or ""
    limit = request.args.get('limit') or 20
    offset = request.args.get('offset') or 0

    model = request.args.get('model')
    _type = request.args.get('type')
    platform = request.args.get('platform')
    vendor = request.args.get('vendor')

    public_model = "  is_public IS TRUE"
    all_my_model = " owner_id={uid}"
    no_filt_model = " (is_public IS TRUE OR owner_id={uid})"
    split_page = " ORDER BY id DESC LIMIT {limit} OFFSET {offset};".format(limit=limit, offset=offset)

    filt = ""
    if model:
        filt = " AND model = '{}'".format(model)
    if _type:
        if filt:
            filt = filt + " AND type = '{}'".format(_type)
        else:
            filt = " AND type = '{}'".format(_type)
    if platform:
        if filt:
            filt = filt + " AND platform = '{}'".format(platform)
        else:
            filt = " AND platform = '{}'".format(platform)
    if vendor:
        if filt:
            filt = filt + " AND vendor = '{}'".format(vendor)
        else:
            filt = " AND vendor = '{}'".format(vendor)

    if not my_model:
        query_models_cmd = query_models_sql + no_filt_model.format(uid=uid) + filt + split_page
        query_total_models_cmd = query_total_models_sql + no_filt_model.format(uid=uid) + filt
    elif my_model == 'false':
        query_models_cmd = query_models_sql + public_model + filt + split_page
        query_total_models_cmd = query_total_models_sql + public_model + filt
    else:
        query_models_cmd = query_models_sql + all_my_model.format(uid=uid) + filt + split_page
        query_total_models_cmd = query_total_models_sql + all_my_model.format(uid=uid) + filt
    request.cursor.execute(query_models_cmd)
    models = request.cursor.fetchall()

    request.cursor.execute(query_total_models_cmd)
    total = request.cursor.fetchone()[0]

    results = OrderedDict()
    results['total'] = total
    results['limit'] = limit
    results['offset'] = offset

    results['models'] = []
    for model in models:
        model = ModelInfo._make(model)._asdict()
        if model['owner_id'] == int(uid):
            model['is_owner'] = True
        else:
            model['is_owner'] = False
        del model['owner_id']
        results['models'].append(model)

    return jsonify(results)


@model_bp.route("", methods=["POST"])
def create_model_view():
    """
    Create a model
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    model = get_json(request).get('model')
    _type = get_json(request).get('type')
    platform = get_json(request).get('platform')
    vendor = get_json(request).get('vendor')

    if not check_is_oxm(request.cursor, user_id=uid):
        return jsonify({
            'status': 'fail',
            'message': 'Only OXM can create model'
        })

    if check_model_exist(request.cursor, model, _type, platform, vendor):
        return jsonify({
            'status': 'fail',
            'message': 'Model already exist, pick another one.'
        })

    if exceed_model_max_limit(request.cursor, user_id=uid):
        return jsonify({
            'status': 'fail',
            'message': 'Exceed the max limit model can create'
        })

    try:
        model_id = create_model(request.cursor, model, _type, platform, vendor, user_id=uid)
        request.conn.commit()

        return jsonify({
            'status': 'success',
            'message': 'Success to create model',
            'model_id': model_id
        })
    except Exception as e:
        error_msg = 'Exception, fail to create model.'
        if IS_DEBUG:
            raise DCCAException(error_msg + ' =>' + str(e))
        else:
            raise DCCAException(error_msg)


@model_bp.route("", methods=["DELETE"])
def delete_model():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    model_id = get_json(request).get('model_id')

    if not check_model_owner(request.cursor, model_id, user_id=uid):
        return jsonify({
            'status': 'fail',
            'message': 'You are not the owner, refuse to access. Or model not exist'
        })

    if binding_to_devices(request.cursor, model_id):
        device_names = bind_to_device_ids(request.cursor, model_id)

        return jsonify({
            'status': 'fail',
            'message': 'This model has been binded to other devices, remove them first.the currently bound device is {}'.format(
                device_names)
        })

    if binding_to_solutions(request.cursor, model_id):
        solution_names = query_solution_name(request.cursor, model_id, user_id=uid)

        return jsonify({
            'status': 'fail',
            'message': 'This model has been binded to other solutions, permamently remove them first.The solution for this model binding is {}'.format(
                solution_names)
        })

    # Not my wish that model binds to dcca_ass_host_model
    if binding_to_ass_host_model(request.cursor, model_id):
        device_ids = bind_to_device_ids(request.cursor, model_id)
        device_names = []

        for device_id in device_ids:
            device_names.append(query_device_name(request.cursor, device_id, user_id=uid))
        return jsonify({
            'status': 'fail',
            'message': 'This model has been binded to some devices, permamently remove them before remove.The device currently binding this model is {}'.format(
                device_ids)
        })

    try:
        request.cursor.execute(delete_model_by_id_sql, (model_id,))
        request.conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'Success to delete model. ID: {}'.format(model_id)
        })
    except Exception:
        raise DCCAException('Error happened when delete model #3')


@model_bp.route("/<model_id>", methods=["GET"])
def query_one_model(model_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    request.cursor.execute(query_model_by_id_sql, (model_id,))
    model = request.cursor.fetchone()
    if not model:
        return jsonify(None)
    else:
        model = Model._make(model)._asdict()
        if model['owner_id'] == int(uid):
            model['is_owner'] = True
        else:
            model['is_owner'] = False
        del model['owner_id']

        return jsonify(model)
