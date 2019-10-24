# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import OrderedDict

from flask import Blueprint, jsonify, request

from edgescale_pymodels.ischema import VendorSchema
from edgescale_pymodels.user_models import DccaVendor
from edgescale_pymodels.constants import *
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import check_json
from edgescale_pyutils.exception_utils import InvalidInputException, DCCAException

vendor_v2_bp = Blueprint("vendor-v2", __name__)


@vendor_v2_bp.route("", methods=["GET"])
def query_all_vendors():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit', 10)
    offset = request.args.get('offset', 0)
    filter_name = request.args.get('filter_name', "")
    order_by = request.args.get('orderBy', "updated_at")
    order_type = request.args.get('orderType', "desc")

    vendors, total = DccaVendor.query_all(limit, offset, filter_name, order_by, order_type)

    data = [vendor.as_dict(schema=VendorSchema) for vendor in vendors]

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = total
    results['vendors'] = data

    return jsonify(results)


@vendor_v2_bp.route("", methods=["POST"])
def create_vendor():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': NOT_ADMIN_CANNOT_CREATE_MSG
        })

    check_json(request)
    name = get_json(request).get("name")
    is_public = get_json(request).get("is_public") or False
    if not name:
        raise InvalidInputException("vendor name is empty.")

    new_item = DccaVendor(name, is_public)
    try:
        status = DccaVendor.create_one(new_item)
    except Exception:
        raise DCCAException("Create vendor failed")

    return jsonify(status)


@vendor_v2_bp.route("/<vendor_id>", methods=["GET"])
def query_one_vendor(vendor_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': NOT_ADMIN_CANNOT_CREATE_MSG
        })

    vendor = DccaVendor.query_one(vendor_id).as_dict(schema=VendorSchema)

    return jsonify(vendor)


@vendor_v2_bp.route("/<vendor_id>", methods=["PUT"])
def update_vendor(vendor_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': NOT_ADMIN_CANNOT_CREATE_MSG
        })

    check_json(request)
    name = get_json(request).get("name")
    if not name:
        raise InvalidInputException("vendor name is empty.")

    try:
        status = DccaVendor.update_one(vendor_id, name)
    except Exception:
        raise DCCAException("Update vendor failed")

    return jsonify(status)


@vendor_v2_bp.route("/<vendor_id>", methods=["DELETE"])
def remove_vendor(vendor_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': NOT_ADMIN_CANNOT_CREATE_MSG
        })

    try:
        status = DccaVendor.delete_one(vendor_id)
    except Exception:
        raise DCCAException("Delete vendor failed")

    return jsonify(status)
