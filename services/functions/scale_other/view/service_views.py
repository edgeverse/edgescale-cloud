# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify
import uuid

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import check_json
from model import IS_DEBUG
from model.constants import *
from utils import *

service_bp = Blueprint("service", __name__)


@service_bp.route("", methods=["GET"])
def list_all_available_services():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') or 20
    offset = request.args.get('offset') or 0

    request.cursor.execute(count_all_services_sql, (uid,))
    size = request.cursor.fetchone()[0]

    request.cursor.execute(query_all_services_sql, (uid, limit, offset))
    _services = request.cursor.fetchall()

    results = OrderedDict()
    results['total'] = size
    results['services'] = []

    for _service in _services:
        service = make_service(_service)
        results['services'].append(service)

    return jsonify(results)


# @service_bp.route("", methods=["POST"])
def create_service_view():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    name = get_json(request).get('name')
    model_id = get_json(request).get('model_id')

    cloudConfig = get_json(request).get("cloudConfig", {})
    protocal = cloudConfig.get('protocal')
    cipher_suite = cloudConfig.get('cipherSuite')

    serverCertificate = cloudConfig.get('serverCertificate', {})
    server_certificate_format = serverCertificate.get('format')
    server_certificate_key = serverCertificate.get('key')

    connection_url = cloudConfig.get('connectionUrl', {}).get("url")
    config = cloudConfig.get('config')

    signingCertificate = get_json(request).get("signingCertificate", {})
    signing_certificate_format = signingCertificate.get('format')
    signing_certificate_key = signingCertificate.get('key')

    result = create_param_validate(cursor=request.cursor, name=name, protocal=protocal, cipher_suite=cipher_suite,
                                   connection_url=connection_url, config=config,
                                   server_certificate_format=server_certificate_format,
                                   server_certificate_key=server_certificate_key,
                                   signing_certificate_format=signing_certificate_format,
                                   signing_certificate_key=signing_certificate_key,
                                   model_id=model_id, uid=uid)

    if result['status'] == 'Invalid':
        return jsonify(result)

    try:
        request.cursor.execute(create_service_sql, (name, protocal, cipher_suite, server_certificate_format,
                                                    server_certificate_key, connection_url, config,
                                                    signing_certificate_format, signing_certificate_key, uid))
    except Exception:
        if IS_DEBUG:
            import traceback
            traceback.print_exc()
        raise DCCAException('Exception to create service')

    service_id = request.cursor.fetchone()[0]
    service_uid = uuid.uuid5(uuid.NAMESPACE_DNS, str(service_id)).hex

    try:
        request.cursor.execute(update_service_uid_sql, (service_uid, service_id))
    except Exception:
        raise DCCAException('Exception to update service uid')

    try:
        request.cursor.execute(create_service_model_map_sql, (model_id, service_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception to bind service to model')

    return jsonify({
        'status': 'success',
        'message': 'Success to create service',
        'id': service_uid
    })


@service_bp.route("/common", methods=["GET"])
def query_all_common_service():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    request.cursor.execute(query_all_common_service_sql, (uid, ))
    _services = request.cursor.fetchall()

    services = []
    for serv in _services:
        service = CommonService._make(serv)._asdict()
        services.append(service)

    return jsonify(services)


@service_bp.route("/common", methods=["POST"])
def create_common_service():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    name = get_json(request).get('name')
    url = get_json(request).get('url')
    port = get_json(request).get('port')
    access_token = get_json(request).get('access_token')

    try:
        service_id = create_service(request.cursor, name, url, port, access_token, user_id=uid)
        request.conn.commit()
    except Exception as e:
        raise DCCAException(make_error_msg(IS_DEBUG, 'Exception, fail to create common service', str(e)))

    return jsonify({
        'status': 'success',
        'message': 'Success to create service ID',
        'id': service_id
    })


# @service_bp.route("/<service_id>", methods=["GET"])
def list_specific_service(service_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    service = query_service(request.cursor, uid, service_id)
    if not service:
        return jsonify({
            'status': 'fail',
            'message': 'Service not exist or you are not the owner.'
        })

    return jsonify(service)


# @service_bp.route("/<service_id>", methods=["PUT"])
def update_specific_service(service_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    name = get_json(request).get('name')
    cloudConfig = get_json(request).get("cloudConfig", {})
    protocal = cloudConfig.get('protocal')
    cipher_suite = cloudConfig.get('cipherSuite')

    serverCertificate = cloudConfig.get("serverCertificate", {})
    server_certificate_format = serverCertificate.get('format')
    server_certificate_key = serverCertificate.get('key')

    connection_url = cloudConfig.get('connectionUrl')
    config = cloudConfig.get('config')

    signingCertificate = get_json(request).get("signingCertificate", {})
    signing_certificate_format = signingCertificate.get('format')
    signing_certificate_key = signingCertificate.get('key')

    result = update_param_validate(cursor=request.cursor, name=name, protocal=protocal, cipher_suite=cipher_suite,
                                   connection_url=connection_url, config=config,
                                   server_certificate_format=server_certificate_format,
                                   server_certificate_key=server_certificate_key,
                                   signing_certificate_format=signing_certificate_format,
                                   signing_certificate_key=signing_certificate_key)

    if result['status'] == 'Invalid':
        return jsonify(result)

    _variables = {}
    if name:
        _variables['name'] = name

    if protocal:
        _variables['protocal'] = protocal

    if cipher_suite:
        _variables['cipher_suite'] = cipher_suite

    if server_certificate_format:
        _variables['server_certificate_format'] = server_certificate_format

    if server_certificate_key:
        _variables['server_certificate_key'] = server_certificate_key

    if connection_url:
        _variables['connection_url'] = connection_url

    if config:
        _variables['config'] = config

    if signing_certificate_format:
        _variables['signing_certificate_format'] = signing_certificate_format

    if signing_certificate_key:
        _variables['signing_certificate_key'] = signing_certificate_key

    update_sql = 'UPDATE dcca_services SET '
    index = 0
    var_size = len(_variables)
    var_values = []
    for k, v in list(_variables.items()):
        update_sql += '{key}=%s'.format(key=k)
        if index != var_size - 1:
            update_sql += ', '
        var_values.append(v)
        index += 1

    update_sql += ' WHERE uid=%s ;'
    var_values.append(service_id)

    try:
        request.cursor.execute(update_sql, tuple(var_values))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to update service')

    return jsonify({
        'status': 'success',
        'message': 'Success to update service'
    })


# @service_bp.route("/<service_id>", methods=["DELETE"])
def delete_service(service_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    service = query_service(request.cursor, uid, service_id)
    if not service:
        return jsonify({
            'status': 'fail',
            'message': 'Service not exist or you are not the owner.'
        })

    try:
        request.cursor.execute(delete_service_by_id_sql, (service_id,))
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception to remove service')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove the service'
    })


@service_bp.route("/<service_id>/common", methods=["PUT"])
def modify_common_service(service_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    name = get_json(request).get('name')
    url = get_json(request).get('url')
    port = get_json(request).get('port')
    access_token = get_json(request).get('access_token')

    if not is_service_owner(request.cursor, user_id=uid, service_id=service_id):
        return jsonify({
            'status': 'fail',
            'message': 'Not the service owner or the service cannot access.'
        })

    try:
        update_service(request.cursor, name, url, port, access_token, service_id)
        request.conn.commit()
    except Exception as e:
        raise DCCAException(make_error_msg(IS_DEBUG, 'Exception, fail to update common service.', str(e)))

    return jsonify({
        'status': 'success',
        'message': 'Success to update the commont service'
    })


@service_bp.route("/<service_id>/common", methods=["DELETE"])
def remove_one_common_service(service_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not service_id:
        return jsonify({
            'status': 'fail',
            'message': 'Service ID cannot be empty.'
        })

    if not is_service_owner(request.cursor, user_id=uid, service_id=service_id):
        return jsonify({
            'status': 'fail',
            'message': 'Not the service owner or the service cannot access.'
        })

    try:
        remove_one_service(request.cursor, service_id)
        request.conn.commit()
    except Exception as e:
        raise DCCAException(make_error_msg(IS_DEBUG, 'Exception, fail to remove common service.', str(e)))

    return jsonify({
        'status': 'success',
        'message': 'Success to remove common service'
    })
