# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import OrderedDict
from datetime import datetime

from flask import Blueprint, jsonify, request

from model import *
from utils import *
from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pymodels.device_models import Host
from edgescale_pymodels.ischema import CustomerSchema, DeviceShortSchema
from edgescale_pymodels.user_models import DccaCustomer, DccaUser
from edgescale_pyutils.model_utils import ctx
from edgescale_pyutils.param_utils import empty_check, check_json
from edgescale_pyutils.view_utils import get_oemid, get_json

custm_bp = Blueprint("customer-v2", __name__)


@custm_bp.route("", methods=["GET"])
def query_all_customers():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else 20
    offset = request.args.get('offset') if request.args.get('offset') else 0
    filter_name = request.args.get('filter_name', '')

    customers, total = DccaCustomer.query_all(filter_name, limit=limit, offset=offset)

    data = []
    for cust in customers:
        data.append(cust.as_dict(schema=CustomerSchema))

    result = OrderedDict()
    result['limit'] = limit
    result['offset'] = offset
    result['total'] = total
    result['customers'] = data

    return jsonify(result)


@custm_bp.route("", methods=["POST"])
def create_one_customer():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    name = get_json(request).get('name')
    description = get_json(request).get('description')

    cust = DccaCustomer(name, description)
    try:
        session.add(cust)
        session.commit()
    except Exception:
        raise DCCAException('Fail to create customer')

    return jsonify({
        'status': 'success',
        'message': 'Success to create customer',
        'data': cust.as_dict(schema=CustomerSchema)
    })


@custm_bp.route("/<customer_id>", methods=["GET"])
def query_one_customer(customer_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(customer_id, error_message='The "customer_id" can not be empty.')

    customer = DccaCustomer.query_by_id(customer_id)
    empty_check(customer, error_message='Not exist or cannot accessable.')

    return jsonify(customer.as_dict(schema=CustomerSchema))


@custm_bp.route("/<customer_id>", methods=["PUT"])
def modify_customer(customer_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    name = get_json(request).get('name')
    is_active = get_json(request).get('is_active')
    description = get_json(request).get('description')

    empty_check(customer_id, error_message='The "customer_id" can not be empty.')

    customer = DccaCustomer.query_by_id(customer_id)
    empty_check(customer, error_message='Not exist or cannot accessable.')

    if name:
        customer.name = name

    if is_active is not None:
        customer.is_active = is_active

    if description:
        customer.description = description

    customer.updated_at = datetime.utcnow()
    try:
        session.add(customer)
        session.commit()
    except Exception:
        raise DCCAException('Fail to update customer')

    return jsonify({
        'status': 'success',
        'message': 'Success to update customer',
        'customer': customer.as_dict(schema=CustomerSchema)
    })


@custm_bp.route("/<customer_id>", methods=["DELETE"])
def delete_one_customer(customer_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(customer_id, error_message='The "customer_id" can not be empty.')

    customer = DccaCustomer.query_by_id(customer_id)
    empty_check(customer, error_message='Not exist or cannot accessable.')

    try:
        session.delete(customer)
        session.commit()
    except Exception:
        if IS_DEBUG:
            import traceback
            traceback.print_exc()
        raise DCCAException('Fail to delete customer')

    return jsonify({
        'status': 'success',
        'message': 'Success to delete customer',
        'customer': customer.as_dict(schema=CustomerSchema)
    })


@custm_bp.route("/<customer_id>/devices", methods=["POST"])
def batch_bind_customer_to_device(customer_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(customer_id, error_message='The "customer_id" can not be empty.')

    customer = DccaCustomer.query_by_id(customer_id)
    empty_check(customer, error_message='The customer not exists or cannot accessable.')

    check_json(request)
    device_ids = get_json(request).get('device_ids', [])
    devices = Host.batch_bind_customer(device_ids, customer)

    data = []
    success = set()
    try:
        for device in devices:
            data.append(device.as_dict(schema=DeviceShortSchema))
            success.add(device.id)
            session.add(device)
        session.commit()
    except Exception:
        raise DCCAException('Fail to bind customer to devices')

    results = OrderedDict()
    results['customer'] = customer.as_dict(schema=CustomerSchema)
    results['devices'] = data
    results['failure'] = list(set(device_ids) - success)

    return jsonify(results)
