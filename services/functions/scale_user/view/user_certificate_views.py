# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

#! -*- coding: utf-8 -*-

from flask import Blueprint, jsonify, request

from model import *
from utils import *
from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import check_json

users_cert_bp = Blueprint("users_certificate", __name__)


@users_cert_bp.route("/certificate", methods=["GET"])
def query_certificate():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    try:
        solu_cert = query_solution_certificate(request.cursor, user_id=uid)
    except Exception:
        raise DCCAException('Fail to revoke the cert from user')
    return jsonify(solu_cert)


@users_cert_bp.route("/certificate", methods=["POST"])
def create_certificate():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    cert_body = get_json(request).get('body')
    cert_private_key = get_json(request).get('private_key')
    cert_chain = get_json(request).get('chain')

    result = validate_create_cert(request.cursor, user_id=uid, cert_body=cert_body,
                                  cert_private_key=cert_private_key, cert_chain=cert_chain)

    if result['status'] == 'fail':
        return jsonify(result)

    try:
        create_solution_cert(request.cursor, cert_body, cert_private_key, cert_chain, uid)
        request.conn.commit()
    except Exception as e:
        error_msg = 'Fail to create solution certificate.'
        if IS_DEBUG:
            error_msg += str(e)
        raise DCCAException(error_msg)

    return jsonify({
        'status': 'success',
        'message': 'Success to create certificate.'
    })


@users_cert_bp.route("/certificate", methods=["PUT"])
def modify_certificate():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    body = get_json(request).get('body')
    private_key = get_json(request).get('private_key')
    chain = get_json(request).get('chain')

    update_items = {}
    if body:
        update_items['body'] = body

    if private_key:
        update_items['private_key'] = private_key

    if chain or chain is None:
        update_items['chain'] = chain

    try:
        update_solution_certificate(request.cursor, uid, update_items)
        request.conn.commit()
    except Exception as e:
        raise DCCAException(str(e))

    return jsonify({
        'status': 'success',
        'message': 'Success to modify certificate'
    })


@users_cert_bp.route("/certificate", methods=["DELETE"])
def remove_certificate():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    try:
        remove_solution_certificate(request.cursor, user_id=uid)
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception, fail to remove solution certificate.')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove certificate'
    })
