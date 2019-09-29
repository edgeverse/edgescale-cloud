# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from edgescale_pymodels.nametuples import User, LimitType, Certificate, AccountTypes
from edgescale_pyutils.auth_utils import encrypt_with_salt, make_token, encrypt_with_random_salt
from edgescale_pyutils.common_utils import _form_warning
from edgescale_pyutils.exception_utils import DCCAException
from model.raw_sqls import *


def verify_user(cursor, user_id, password):
    query_user_password_by_id_cmd = query_user_password_by_id_sql.format(uid=user_id)
    cursor.execute(query_user_password_by_id_cmd)
    user = cursor.fetchone()
    if user is None:
        return False, None

    user = User._make(user)
    encrypted = encrypt_with_salt(password, user.salt)
    if encrypted == user.password:
        token = make_token(user)
        return user.uid, token
    else:
        return None, None


def update_password(conn, cursor, user_id, password):
    password, salt = encrypt_with_random_salt(password)
    try:
        cursor.execute(update_password_sql, (password, salt, user_id))
        conn.commit()
    except Exception:
        raise DCCAException('Fail to update user\' password')


def query_limit_type(cursor, limit_type_id):
    cursor.execute(query_limit_type_sql, (limit_type_id, ))
    _limit_type = cursor.fetchone()
    if _limit_type:
        return LimitType._make(_limit_type)
    else:
        return None


def user_exist(cursor, username):
    cursor.execute(query_user_id_sql, (username,))
    user = cursor.fetchone()
    if user:
        return True, user[0]
    else:
        return False, None


def _certificate_exist(cursor, user_id):
    cursor.execute(check_cert_exist_sql, (user_id, ))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def validate_create_cert(cursor, user_id, **args):
    # Only the OXM can create certificate
    if _certificate_exist(cursor, user_id):
        return _form_warning('Certificate already exist.')

    for k, v in list(args.items()):
        if k == 'cert_body':
            if not v:
                return _form_warning('Certificate body cannot be empty.')
        elif k == 'cert_private_key':
            if not v:
                return _form_warning('Certificate private key cannot be empty.')
        elif k == 'cert_chain':
            pass

    return {
        'status': 'success',
    }


def create_solution_cert(cursor, body, private_key, chain, user_id):
    cursor.execute(create_solution_cert_sql, (body, private_key, chain, user_id))
    solu_cert_id = cursor.fetchone()[0]
    return solu_cert_id


def query_solution_certificate(cursor, user_id):
    cursor.execute(query_solu_cert_sql, (user_id, ))
    _solu_cert = cursor.fetchone()
    if _solu_cert:
        solu_cert = Certificate._make(_solu_cert)
        return solu_cert._asdict()
    else:
        return {}


def remove_solution_certificate(cursor, user_id):
    cursor.execute(remove_solu_cert_sql, (user_id, ))


def update_solution_certificate(cursor, user_id, update_items):
    for name, value in list(update_items.items()):
        _condition = "{}=%s ".format(name)
        update_sql = 'UPDATE dcca_certificates SET {} WHERE user_id=%s ;'.format(_condition)
        try:
            cursor.execute(update_sql, (value, user_id, ))
        except Exception:
            raise DCCAException('Exception, fail to update certificate, invalid {}'.format(name))


def query_account_types(cursor):
    cursor.execute(query_account_types_sql)
    account_types = cursor.fetchall()

    data = {
        'account_types': []
    }

    for at in account_types:
        account_types_obj = AccountTypes._make(at)._asdict()
        data['account_types'].append(account_types_obj)

    return data


def check_email_exists(cursor, email):
    count = 0
    cursor.execute(count_email_sql, (email,))
    count += cursor.fetchone()[0]

    cursor.execute(count_email_user_sql, (email,))
    count += cursor.fetchone()[0]

    if count == 0:
        return False
    else:
        return True
