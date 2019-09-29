# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import check_json
from model import *
from model.ischema import *
from utils import *

role_bp = Blueprint("role", __name__)


@role_bp.route("", methods=["GET"])
def query_roles():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    current_user = DccaUser.get_by_id(uid)
    if not current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only admin can modify role'
        })

    limit = request.args.get('limit') if request.args.get('limit') else 10
    offset = request.args.get('offset') if request.args.get('offset') else 0
    filter_name = request.args.get('filter_name')
    order_by = request.args.get('order_by')
    reverse = request.args.get('reverse')

    if reverse == 'true':
        _reverse = True
    else:
        _reverse = False

    roles, total_size = DccaRole.query_all(filter_name, order_by, limit, offset, reverse=_reverse)

    _data = []
    for role in roles:
        _data.append(role.as_dict(schema=RoleSchema))

    result = OrderedDict()
    result['limit'] = limit
    result['offset'] = offset
    result['total'] = total_size
    result['roles'] = _data

    return jsonify(result)


@role_bp.route("", methods=["POST"])
def create_role():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    current_user = DccaUser.get_by_id(uid)
    if not current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only admin can modify role'
        })

    check_json(request)
    name = get_json(request).get('name')
    _desc = get_json(request).get('description')
    resources = get_json(request).get('resources', [])

    role_name_empty(name)
    contain_whitespace(name)
    role_name_taken(name)

    role = DccaRole(name, _desc)
    try:
        session.add(role)
        session.flush()
    except Exception:
        raise DCCAException('Fail to create role')

    not_exist_resources = []
    appended_resources = []
    try:
        for res_id in resources:
            res = DccaPermission.get_by_id(res_id)
            if not res:
                not_exist_resources.append(res_id)

            if res and res not in role.perms:
                role.perms.append(res)
                appended_resources.append(res)

        session.commit()
    except Exception as e:
        if IS_DEBUG:
            print(e)
        raise DCCAException('Fail to append permission to role')

    results = OrderedDict()
    results['status'] = 'success'
    results['message'] = 'Success to create a role'
    results['role'] = role.data(resources=appended_resources)
    results['resource_cannot_access'] = not_exist_resources

    return jsonify(results)


@role_bp.route("/<role_id>", methods=["GET"])
def query_one_role(role_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    role_id_empty(role_id)

    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    return jsonify(role.data())


@role_bp.route("/<role_id>", methods=["PUT"])
def modify_role(role_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    current_user = DccaUser.get_by_id(uid)
    if not current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only admin can modify role'
        })

    check_json(request)
    name = get_json(request).get('name')
    _desc = get_json(request).get('description')
    resources = get_json(request).get('resources')

    role_id_empty(role_id)

    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    if name:
        role.name = name

    if _desc:
        role.description = _desc
    elif _desc == '':
        role.description = ''

    role.updated_at = datetime.utcnow()

    try:
        session.add(role)
        session.flush()
    except Exception:
        raise DCCAException('Fail to modify role')

    if resources:
        try:
            for res_id in resources:
                res = DccaPermission.get_by_id(res_id)
                if res not in role.perms:
                    role.perms.append(res)
        except Exception:
            raise DCCAException('Fail to update role resource')

    try:
        session.commit()
    except Exception:
        raise DCCAException('Fail to commit')

    results = OrderedDict()
    results['status'] = 'success'
    results['message'] = 'Success to update the role'
    results['role'] = role.data()

    return jsonify(results)


@role_bp.route("/<role_id>", methods=["DELETE"])
def remove_role(role_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    current_user = DccaUser.get_by_id(uid)
    if not current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only admin can modify role'
        })

    role_id_empty(role_id)

    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    try:
        role.remove()
        session.commit()
    except Exception as e:
        raise DCCAException('Fail to remove role %s' % e)

    return jsonify({
        'status': 'success',
        'message': 'Success to remove the role',
        'role': {
            'id': role.id,
            'name': role.name,
            'description': role.description
        }
    })


@role_bp.route("/<role_id>/resources/<resource_id>", methods=["POST"])
def bind_resource_to_role(role_id, resource_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    role_id_empty(role_id)
    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    resource_id_empty(resource_id)
    res = DccaPermission.get_by_id(resource_id)
    resource_not_exist(res)

    try:
        role.add_resource(res)
        session.commit()
    except Exception:
        raise DCCAException('Fail to bind resource to role.')

    return jsonify({
        'status': 'success',
        'message': 'Success bind resource to role',
        'role': role.as_dict(schema=RoleSchema),
        'resource': res.as_dict(schema=FullResourceSchema)
    })


@role_bp.route("/<role_id>/resources/<resource_id>", methods=["DELETE"])
def unbind_resource_from_role(role_id, resource_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    role_id_empty(role_id)
    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    resource_id_empty(resource_id)
    res = DccaPermission.get_by_id(resource_id)
    resource_not_exist(res)

    try:
        role.remove_resource(res)
        session.commit()
    except Exception:
        raise DCCAException('Fail to unbind resource from role')

    result = OrderedDict()
    result['status'] = 'success'
    result['message'] = 'Success unbind resource from role'
    result['role'] = role.as_dict(schema=RoleSchema)
    result['resource'] = res.as_dict(schema=FullResourceSchema)
    return jsonify(result)
