# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import check_json
from model import *
from utils import *

resource_bp = Blueprint("resource", __name__)


@resource_bp.route("", methods=["GET"])
def query_resources():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    current_user = DccaUser.get_by_id(uid)
    if not current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only admin can modify role'
        })

    resources = DccaPermission.query_all()
    return jsonify(resources)


@resource_bp.route("", methods=["POST"])
def create_resource():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    name = get_json(request).get('name')
    resource_type = get_json(request).get('resource_type')
    action = get_json(request).get('action')
    url_pattern = get_json(request).get('path')

    contain_whitespace(name)
    duplicate_name(name)
    contain_whitespace(resource_type)
    action_validate(action)
    contain_whitespace(url_pattern)

    try:
        resource = DccaResource(name, action, url_pattern)
        session.add(resource)
        session.flush()

        perm = DccaPermission(name, resource_type, resource)
        session.add(perm)
        session.commit()
    except Exception:
        raise DCCAException('Fail to create resource')

    return jsonify({
        'status': 'success',
        'message': 'Success tgrant_user_one_roleo create resource',
        'resource': perm.as_dict(schema=FullResourceSchema)
    })


@resource_bp.route("/<resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    resource_id_empty(resource_id)

    res = DccaPermission.get_by_id(resource_id)
    resource_not_exist(res)

    data_to_remove = res.as_dict(schema=ResourceSchema)

    try:
        res.remove()
        session.commit()
    except Exception:
        raise DCCAException('Fail to remove resource.')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove resourece',
        'resource': data_to_remove
    })

