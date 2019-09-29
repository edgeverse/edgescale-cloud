# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.view_utils import get_oemid, get_json
from model.constants import *
from edgescale_pyutils.param_utils import check_json
from utils import *

registry_bp = Blueprint("registry", __name__)


@registry_bp.route("", methods=["GET"])
def query_registries():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    # is_admin = True if request.headers.get('admin') == 'true' else False

    check_json(request)
    limit = request.args.get('limit', 2000)
    offset = request.args.get('offset', 0)
    filter_text = request.args.get('filter_text') or ''
    filter_type = request.args.get('filter_type', 'public')

    all_sql = query_all_registries_sql
    total_sql = query_total_registries_sql
    with_status_sql = 'user_id={user_id} AND is_public={is_public} ORDER BY created_at DESC LIMIT {limit} OFFSET {offset};'
    no_status_sql = '(user_id={user_id} OR is_public IS TRUE) ORDER BY created_at DESC LIMIT {limit} OFFSET {offset};'

    if filter_text:
        all_sql += "name like '%{filter_text}%' AND "
        total_sql += "name like '%{filter_text}%' AND "

    if filter_type == 'private':
        filter_type = False
        all_sql += with_status_sql
        total_sql += 'user_id={user_id} AND is_public={is_public};'
    else:
        filter_type = True
        all_sql += no_status_sql
        total_sql += '(user_id={user_id} OR is_public IS TRUE);'

    query_mirrors_cmd = all_sql.format(user_id=uid, is_public=filter_type, limit=limit,
                                       offset=offset, filter_text=filter_text)
    query_total_mirrors_cmd = total_sql.format(user_id=uid, filter_text=filter_text,
                                               is_public=filter_type)

    request.cursor.execute(query_mirrors_cmd)
    registries = request.cursor.fetchall()
    request.cursor.execute(query_total_mirrors_cmd)
    total = request.cursor.fetchone()[0]

    results = {
        "registries": [],
        "limit": limit,
        "offset": offset,
        "total": total
    }

    for reg in registries:
        reg = RegistryShort._make(reg)
        reg = reg._asdict()
        reg["created_at"] = str(reg["created_at"])
        results['registries'].append(reg)

    return jsonify(results)


@registry_bp.route("", methods=["POST"])
def add_registry():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    is_admin = True if request.headers.get('admin') == 'true' else False
    is_public = True if get_json(request).get('is_public') else False
    name = get_json(request).get('name')

    if is_public and not is_admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only administrator can add public registry'
        })

    if is_public and is_admin:
        create_registry_cmd = create_registry_sql.format(name=name, user_id=uid, is_public='TRUE')
    else:
        create_registry_cmd = create_registry_sql.format(name=name, user_id=uid, is_public='FALSE')

    try:
        request.cursor.execute(create_registry_cmd)
        request.conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'Success to create docker registry'
        })
    except Exception:
        raise DCCAException('Fail to create docker registry')


@registry_bp.route("/login", methods=["GET"])
def get_login():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    try:
        username, email = query_user_name(request.cursor, uid)
        request.conn.commit()
        result = get_docker_login_cmd(username, email)
        return jsonify(result)
    except Exception as e:
        raise DCCAException(str(e))


@registry_bp.route("/<registry_id>", methods=["DELETE"])
def delete_registry(registry_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False

    if not registry_id:
        return jsonify({
            'status': 'fail',
            'message': 'The "registry_id" can not be empty'
        })

    query_registry_cmd = query_registry_sql.format(registry_id=registry_id)
    request.cursor.execute(query_registry_cmd)
    registry = request.cursor.fetchone()
    if not registry:
        return jsonify({
            'status': 'fail',
            'message': 'Registry not exist'
        })

    registry = RegistryFull._make(registry)
    if registry.owner_id != uid and not registry.public:
        return jsonify({
            'status': 'fail',
            'message': 'Not authorized to this registry'
        })

    if registry.public and not is_admin:
        # TODO We should allow not only administrator but also authorized user to delete registry
        return jsonify({
            'status': 'fail',
            'message': 'Only administrator can delete public registry'
        })

    remove_registry_cmd = remove_registry_sql.format(registry_id=registry.id)
    remove_softapp_cmd = remove_softapp_sql.format(mirror_id=registry.id)
    query_softapps_cmd = query_softapps_sql.format(mirror_id=registry.id)
    request.cursor.execute(query_softapps_cmd)
    soft_app_ids = request.cursor.fetchall()

    try:
        for sid in soft_app_ids:
            remove_da_inst_cmd = remove_da_inst_sql.format(softapp_id=sid[0])
            request.cursor.execute(remove_da_inst_cmd)
        request.cursor.execute(remove_softapp_cmd)
        request.cursor.execute(remove_registry_cmd)
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to remove registry')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove registry'
    })
