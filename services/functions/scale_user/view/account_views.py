# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import OrderedDict

from flask import Blueprint, jsonify, request

from edgescale_pyutils.param_utils import check_json
from model import SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PWD
from utils import *
from view.users_views import create_user
from edgescale_pymodels.ischema import AccountSchema
from edgescale_pymodels.nametuples import AccountShort
from edgescale_pymodels.user_models import DccaAccount
from edgescale_pyutils.common_utils import rand_generator, generate_oemid, bin_to_hex
from edgescale_pyutils.view_utils import get_oemid, send_email, get_json
from edgescale_pymodels.constants import *

account_bp = Blueprint("account", __name__)


@account_bp.route("", methods=["GET"])
def query_all_account_applications():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit', DEFAULT_LIMIT)
    offset = request.args.get('offset', DEFAULT_OFFSET)
    orderBy = request.args.get('orderBy', '')
    orderType = request.args.get('orderType', 'desc')
    filter_text = request.args.get('filter_text', '')
    filter_type = request.args.get('filter_type', '')
    filter_status = request.args.get('filter_status', '')

    if orderType not in ('asc', 'desc'):
        return jsonify({
            'status': "fail",
            'message': "Invalid order type"
        })

    if orderBy not in ('created_at', 'status', ''):
        return jsonify({
            'status': "fail",
            'message': "Invalid orderBy value"
        })

    if filter_type not in ('oem', 'user', ''):
        return jsonify({
            'status': "fail",
            'message': "Invalid account type"
        })

    if filter_status not in ('approve', 'reject', 'pending', ''):
        return jsonify({
            'status': "fail",
            'message': "Invalid account type"
        })

    filter_type = filter_type_convert.get(filter_type)
    filter_status = filter_status_convert.get(filter_status)

    accounts, size = DccaAccount.query_all(filter_text, filter_type, filter_status, orderBy, orderType, limit, offset)

    results = OrderedDict()
    results['total'] = size
    results['orderType'] = orderType
    results['orderBy'] = orderBy
    results['limit'] = limit
    results['offset'] = offset
    results['accounts'] = []

    for account in accounts:
        results['accounts'].append(account.as_dict(schema=AccountSchema))

    return jsonify(results)


@account_bp.route("", methods=["POST"])
def apply_for_special_account():
    check_json(request)
    first_name = get_json(request).get('first_name')
    last_name = get_json(request).get('last_name')
    company_name = get_json(request).get('company_name')
    telephone = get_json(request).get('telephone')
    email = get_json(request).get('email')
    job_title = get_json(request).get('job_title')
    account_type_id = get_json(request).get('account_type_id')

    if not (first_name
            and last_name and company_name
            and email and account_type_id):
        return jsonify({
            'status': 'fail',
            'message': 'Items cannot be empty'
        })

    if check_email_exists(request.cursor, email):
        return jsonify({
            'status': 'fail',
            'message': 'Email already exists'
        })

    _data = query_account_types(request.cursor)
    if int(account_type_id) not in [at['id'] for at in _data['account_types']]:
        return jsonify({
            'status': 'fail',
            'message': 'Invalid account type'
        })

    try:
        request.cursor.execute(create_accounts_sql, (company_name, telephone, email, job_title,
                                                     account_type_id, first_name, last_name))
        a_id = request.cursor.fetchone()[0]
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception when apply for account')

    return jsonify({
        'status': 'success',
        'message': 'Success to apply for accounts',
        'id': a_id
    })


@account_bp.route("/types", methods=["GET"])
def query_account_types_view():
    return jsonify(query_account_types(request.cursor))


@account_bp.route("/<account_id>/manage", methods=["POST"])
def approve_or_reject_account_request(account_id):
    check_json(request)
    action = get_json(request).get('action')
    is_admin = True if request.headers.get('admin') == 'true' else False

    if not account_id:
        return jsonify({
            'status': 'fail',
            'message': 'The "account ID" cannot be empty.'
        })

    if action == ACTION_APPROVE:
        status = REQUEST_STATUS_CODE_APPROVED
    elif action == ACTION_REJECT:
        status = REQUEST_STATUS_CODE_REJECTED
    else:
        return jsonify({
            'status': 'fail',
            'message': 'Invalid action type'
        })

    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': 'Only admin can handle account request'
        })

    try:
        request.cursor.execute(update_accounts_sql, (status, account_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception: update accounts')

    request.cursor.execute(query_account_sql, [account_id])
    account = request.cursor.fetchone()
    account = AccountShort._make(account)
    email = account.email
    account_type_id = account.type_id

    if action == ACTION_APPROVE:
        oem_id = None
        if account_type_id == 2:
            while True:
                oem_id = generate_oemid()
                cmd = count_oem_id_sql.format(oem_id)
                request.cursor.execute(cmd)
                count = int(request.cursor.fetchone()[0])
                if count == 0:
                    break
                continue
        random_password = rand_generator(16)

        result = create_user(username=email, password=random_password, email=email, account_type_id=account_type_id)
        if result['status'] == 'success' \
                or ('status' in result and result['status'] == 'fail' and 'already exist' in result['message']):
            request.cursor.execute(query_oem_id_by_email, (email,))
            oem_id = request.cursor.fetchone()[0]
            if oem_id:
                oem_id = bin_to_hex(oem_id)[2:]
                send_email(SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PWD, email, subject_html_user,
                           body_html_oem.format(account=email, password=random_password, oem_id=oem_id))
            else:
                send_email(SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PWD, email, subject_html_user,
                           body_html_user.format(account=email, password=random_password))
            request.conn.commit()
            return jsonify({
                'status': 'success',
                'message': 'The request has been approved.'
            })
        else:
            request.conn.rollback()
            return jsonify({
                'status': 'fail',
                'message': 'Fail to create account.',
                'reason': result['message']
            })
    else:
        # Only send email to user to tell user that he has been rejected.
        send_email(SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PWD, email, subject_html_user_reject,
                   body_html_user_reject)
        return jsonify({
            'status': 'success',
            'message': 'The request has been rejected.'
        })
