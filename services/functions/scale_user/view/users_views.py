# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

#! -*- coding: utf-8 -*-
from collections import OrderedDict
from datetime import datetime

from flask import Blueprint, request, jsonify

from model import *
from utils import *
from edgescale_pymodels.ischema import RoleSchema, UserSchema, UserItemSchema
from edgescale_pymodels.nametuples import UserAll, UserInfo
from edgescale_pymodels.user_models import DccaUser
from edgescale_pymodels.role_models import DccaRole
from edgescale_pyutils.auth_utils import generate_token, DCCACrypt
from edgescale_pyutils.boto3_utils import s3_folder_exists, create_foler
from edgescale_pyutils.common_utils import strftime, rand_generator, get_all_timezone
from edgescale_pyutils.param_utils import check_username, check_email, user_id_empty, user_not_exist, role_id_empty, \
    role_not_exist, check_json
from edgescale_pymodels.constants import *
from edgescale_pyutils.view_utils import get_oemid, account_str, send_email_reset_pwd, get_json


user_bp = Blueprint("users", __name__)


@user_bp.route("", methods=["GET"])
def get_all():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False

    limit = request.args.get('limit') if request.args.get('limit') else 2000
    offset = request.args.get('offset') if request.args.get('offset') else 0
    filter_text = request.args.get('filter_text') if request.args.get('filter_text') else None

    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': 'You are not administrator, can not able to access this.'
        })

    if filter_text:
        filter_text += '%'
        request.cursor.execute(query_all_users_filter_sql, (filter_text, filter_text, limit, offset))
    else:
        request.cursor.execute(query_all_users_sql, (limit, offset))
    users = request.cursor.fetchall()

    request.cursor.execute(count_all_user_cmd)
    all_size = request.cursor.fetchone()[0]

    results = OrderedDict()
    results['total'] = all_size
    results['offset'] = offset
    results['limit'] = limit

    users_info_list = []
    for user in users:
        user_info = UserAll._make(user)._asdict()
        user_info['created_at'] = strftime(user_info['created_at'])
        user_info['updated_at'] = strftime(user_info['updated_at'])
        users_info_list.append(user_info)
        if user_info['status']:
            user_info['status'] = 'active'
        else:
            user_info['status'] = 'inactive'

    results['users'] = users_info_list
    return jsonify(results)


@user_bp.route("", methods=["PUT"])
def update_user():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    display_name = get_json(request).get('display_name')
    # timezone = get_json(request).get('timezone')

    try:
        request.cursor.execute(update_user_by_id_sql, (display_name, uid))
        request.conn.commit()
    except Exception as e:
        print(e)
        raise DCCAException('Fail to update user')

    return jsonify({
        'status': 'success',
        'message': 'Success to update user'
    })


@user_bp.route("", methods=["POST"])
def send_email_register():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    username = get_json(request).get('username')
    email = get_json(request).get('email')

    is_admin = True if request.headers.get('admin') == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only administrator can create user.'
        })

    password = rand_generator(size=8)

    # random password
    result = create_user(username, password, email)

    if result['status'] == 'fail':
        return jsonify(result)

    token = generate_token(result['uid'])
    account = account_str(username, email)

    # If success to create the user, then send an email
    return jsonify(
        send_email_reset_pwd(SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PWD, email, token, account, HOST_SITE))


def count_user_by_name(username):
    request.cursor.execute(count_user_sql, (username,))
    count = request.cursor.fetchone()[0]
    return count


def create_user(username, password, email, oem_id=None, account_type_id=ACCOUNT_TYPE_COMMON_USER_ID):
    """
    Create a user
    :return:
    """
    result = check_username(username)
    if result:
        return result

    result = check_email(email)
    if result:
        return result

    size = count_user_by_name(username)
    if size != 0:
        return {
            'status': 'fail',
            'message': 'User already exist'
        }

    request.cursor.execute(count_user_email_sql, (email,))
    size = request.cursor.fetchone()[0]
    if size != 0:
        return {
            'error': True,
            'status': 'fail',
            'message': 'Email has been taken'
        }

    password, salt = encrypt_with_random_salt(password)

    try:
        request.cursor.execute(create_user_sql, (username, email, password, salt, False, account_type_id, oem_id))
        user_id = request.cursor.fetchone()[0]
    except Exception:
        raise DCCAException('Fail to create user')

    try:
        request.cursor.execute(grant_user_default_role_sql, (user_id, DEFAULT_ROLE_ID))
    except Exception:
        raise DCCAException('Fail to create user role')


    # Make the limits data
    request.cursor.execute(query_limit_types_sql)
    limit_types = request.cursor.fetchall()

    try:
        for _type in limit_types:
            type_id = _type[0]
            default_max_limit = _type[2]
            default_max_sec = _type[3]
            request.cursor.execute(create_limits_sql, (user_id, type_id, default_max_limit, default_max_sec))

        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to create user limits')

    return {
        'status': 'success',
        'message': 'Success to create an user',
        'uid': str(user_id)
    }


def delete_user_by_name(username):
    try:
        request.cursor.execute(delete_user_by_name_sql, (username,))
        request.conn.commit()
        return True
    except Exception:
        request.conn.rollback()
        return {
            'error': True,
            'status': 'fail',
            'message': 'Exception in delete user by name function'
        }


@user_bp.route("/<user_id>", methods=["GET"])
def query_user_details(user_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin') == 'true' else False

    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': "Only administrator can query user's information."
        })

    request.cursor.execute(query_one_user_sql, (user_id,))
    user = request.cursor.fetchone()
    user = UserAll._make(user)

    _user = user._asdict()
    _user['created_at'] = strftime(_user['created_at'])
    _user['updated_at'] = strftime(_user['updated_at'])
    if _user['status']:
        _user['status'] = 'active'
    else:
        _user['status'] = 'inactive'

    return jsonify(_user)


@user_bp.route("/<user_id>/roles/<role_id>", methods=["POST"])
def grant_user_one_role(user_id, role_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    user_id_empty(user_id)
    user = DccaUser.get_by_id(user_id)
    user_not_exist(user)

    role_id_empty(role_id)
    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    if not user.has_role(role):
        try:
            user.roles.append(role)
            session.add(user)
            session.commit()
        except Exception:
            raise DCCAException('Fail to grant the role to user')

    return jsonify({
        'status': 'success',
        'message': 'Success to grant role to user %s' % user.username,
        'role': role.as_dict(schema=RoleSchema),
        'user': user.as_dict(schema=UserSchema)
    })


@user_bp.route("/<user_id>/roles/<role_id>", methods=["DELETE"])
def revoke_user_one_role(user_id, role_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    user_id_empty(user_id)
    user = DccaUser.get_by_id(user_id)
    user_not_exist(user)

    role_id_empty(role_id)
    role = DccaRole.get_by_id(role_id)
    role_not_exist(role)

    if user.has_role(role):
        try:
            user.revoke_role(role)
            session.add(user)
            session.commit()
        except Exception:
            raise DCCAException('Fail to revoke the role from user')

        return jsonify({
            'status': 'success',
            'message': 'Success to remove role from user',
            'role': role.as_dict(schema=RoleSchema),
            'user': user.as_dict(schema=UserSchema)
        })
    else:
        return jsonify({
            'status': 'success',
            'message': 'User hasn\'t been granted of this role.'
        })


@user_bp.route("/login", methods=["POST"])
def login():
    username = get_json(request).get('username')
    password = get_json(request).get('password')

    result = check_username(username)
    if result:
        return jsonify(result)

    request.cursor.execute(login_user_sql, (username,))
    user = request.cursor.fetchone()

    if user is None:
        return jsonify({
            'status': 'fail',
            'message': 'Incorrect Username or password'
        })

    user = User._make(user)

    if not user.status:
        return jsonify({
            'status': 'fail',
            'message': 'Your account is inactive.'
        })

    encrypted = encrypt_with_salt(password, user.salt)
    if encrypted == user.password:
        token = make_token(user)

        return jsonify({
            'status': 'success',
            'message': 'Success to login',
            'token': token
        })
    else:
        return jsonify({
            'status': 'fail',
            'message': 'Incorrect Username or password'
        })


@user_bp.route("/operations", methods=["POST"])
def change_user_status():
    user_id = get_json(request).get("user_id")
    status = get_json(request).get("status")

    if status:
        if status == 'active':
            status = ACTIVE
        else:
            status = INACTIVE
        try:
            request.cursor.execute(update_user_status, (status, user_id))
            request.conn.commit()
        except Exception:
            raise DCCAException('Operate failed')

        return jsonify({
            'status': 'success',
            'message': 'Operate successfully'
        })


@user_bp.route("/password", methods=["PUT"])
def change_password():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    old_password = get_json(request).get('old_password')
    new_password = get_json(request).get('new_password')
    user_id, _ = verify_user(request.cursor, uid, old_password)

    if user_id:
        update_password(request.conn, request.cursor, uid, new_password)
        return jsonify({
            'status': 'success',
            'message': 'Success to change password'
        })
    else:
        return jsonify({
            'status': 'fail',
            'message': 'Invalid username or password'
        })


@user_bp.route("/password/reset", methods=["POST"])
def confirm_to_reset_password():
    check_json(request)
    account = get_json(request).get('account')

    if not account:
        return jsonify({
            'status': 'fail',
            'message': 'Username or email cannot be empty'
        })

    request.cursor.execute(query_user_by_name_email_sql, (account, account))

    user = request.cursor.fetchone()
    if not user:
        return jsonify({
            'status': 'fail',
            'message': 'Invalid username or email'
        })

    user = UserInfo._make(user)
    _user = user._asdict()
    username = _user['username']
    email = _user['email']

    token = generate_token(user.uid)
    account = account_str(username, email)
    return jsonify(send_email_reset_pwd(SMTP_HOST,SMTP_PORT,ADMIN_EMAIL,ADMIN_EMAIL_PWD,email,token, account, HOST_SITE))


@user_bp.route("/password/reset", methods=["PUT"])
def reset_password():
    check_json(request)
    token = get_json(request).get('token')
    password = get_json(request).get('password')

    crypter = DCCACrypt(MAIL_TOKEN_KEY)
    decrypt_token = crypter.decrypt(token)
    user_id, time_str = decrypt_token.split(' ')

    delta = datetime.now() - datetime.strptime(time_str, TIME_FORMAT_STR)
    if delta.seconds / 60 > DEFAULT_MAIL_TOKEN_TIMEOUT:
        return jsonify({
            'status': 'fail',
            'message': 'The token timeout '
        })
    else:
        password_hash, password_salt = encrypt_with_random_salt(password)
        try:
            request.cursor.execute(update_password_confirm_email_sql, (password_hash, password_salt, user_id))
            request.conn.commit()
        except Exception:
            raise DCCAException('Fail to reset password')

        return jsonify({
            'status': 'success',
            'message': 'Success to reset password'
        })


@user_bp.route("/self", methods=["GET"])
def query_self_role_resource():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    current_user = DccaUser.get_by_id(uid)
    user = current_user.as_dict(schema=UserItemSchema)
    user['permissions'] = current_user.role_perm()
    return jsonify(user)


@user_bp.route("/self", methods=["PUT"])
def update_user_self():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    display_name = get_json(request).get('display_name') or ""
    image = get_json(request).get('image')

    try:
        request.cursor.execute(update_user_by_id_nullable_sql, (display_name, image, uid))
        request.conn.commit()

        return jsonify({
            'status': 'success',
            'message': 'Success to update user\'s information.'
        })
    except Exception:
        raise DCCAException('Exception when update user\'s account')


@user_bp.route("/timezones", methods=["GET"])
def query_timezones():
    return jsonify({'timezone': get_all_timezone()})
