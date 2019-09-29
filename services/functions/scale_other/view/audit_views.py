# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.param_utils import check_permission
from edgescale_pyutils.view_utils import get_oemid, get_json
from model.constants import *
from utils import *

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("", methods=["GET"])
def query_audit_view():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') or 20
    offset = request.args.get('offset') or 0
    filter_text = request.args.get('filter_text') or ''
    filter_type = request.args.get('filter_type') or ''
    order_by = request.args.get('orderBy') or 'created_at'
    order_type = request.args.get('orderType') or 'desc'

    if order_type not in ['asc', 'desc']:
        return jsonify({
            'status': "fail",
            'message': "Invalid order type"
        })

    if order_by not in ['created_at', 'status', '']:
        return jsonify({
            'status': "fail",
            'message': "Invalid orderBy value"
        })

    try:
        split = "ORDER BY {order_by} {order_type} LIMIT {limit} OFFSET {offset};"
        if filter_text:
            if filter_type:
                query_audit_sql = query_audit + "WHERE username LIKE '%{filter_text}%' " \
                                                "AND approve_type='{filter_type}' " + split
                query_total_audit_sql = query_total_audit + "WHERE username LIKE '%{filter_text}%' " \
                                                            "AND approve_type='{filter_type}';"
            else:
                query_audit_sql = query_audit + "WHERE username LIKE '%{filter_text}%' " + split
                query_total_audit_sql = query_total_audit + "WHERE username LIKE '%{filter_text}%';"
        else:
            if filter_type:
                query_audit_sql = query_audit + "WHERE approve_type='{filter_type}' " + split
                query_total_audit_sql = query_total_audit + "WHERE approve_type='{filter_type}';"
            else:
                query_audit_sql = query_audit + split
                query_total_audit_sql = query_total_audit

        request.cursor.execute(query_audit_sql.format(filter_text=filter_text, filter_type=filter_type,
                                                      order_by=order_by, order_type=order_type,
                                                      limit=limit, offset=offset))
        audits = request.cursor.fetchall()
        request.cursor.execute(query_total_audit_sql.format(filter_text=filter_text, filter_type=filter_type))
        total = request.cursor.fetchone()[0]

        results = OrderedDict()
        results['orderType'] = order_type
        results['orderBy'] = order_by
        results['offset'] = offset
        results['limit'] = limit
        results['total'] = total
        results['results'] = []

        for a in audits:
            a = Audits._make(a)
            a = a._asdict()
            a["created_at"] = str(a["created_at"])
            results['results'].append(a)

    except Exception as e:
        return jsonify({
            "status": "fail",
            "error": str(e)
        })

    return jsonify(results)


@audit_bp.route("", methods=["POST"])
def create_audit_view():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    approve_type = get_json(request).get('approve_type')
    approve_item = get_json(request).get('approve_item')
    comments = get_json(request).get('description')
    permission = get_json(request).get('permission')

    if approve_type == 'model':
        request.cursor.execute(query_one_model_sql, (approve_item, uid))
        count = request.cursor.fetchone()
        if not count:
            return jsonify({
                'status': "fail",
                'message': "Model not exist or you are not permit to access."
            })

        to_public = check_permission(permission)
        try:
            request.cursor.execute(create_audit_sql, (uid, comments, approve_type, approve_item, to_public))
            audit_id = request.cursor.fetchone()[0]
            request.conn.commit()
        except Exception as e:
            err_msg = "Fail to create request. {}".format(str(e))
            raise DCCAException(err_msg)

        return jsonify({
            "status": "success",
            "message": "Operate successfully",
            "id": audit_id
        })
    return jsonify({
        'status': "fail",
        'message': "Failed to operate"
    })


@audit_bp.route("/<audit_id>", methods=["POST"])
def handler_audit_view(audit_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    action = get_json(request).get('action')

    request.cursor.execute(query_one_audit, (audit_id,))
    audit = request.cursor.fetchone()
    audit = AuditsShort._make(audit)

    if action == 'accept':
        approved = True
        model_id = audit.approve_item
        if audit.to_public:
            is_public = True
        else:
            is_public = False
            other_device = check_device_bind_model(request.cursor, uid, model_id)
            if other_device:
                return jsonify({
                    "status": "fail",
                    "message": "Someone else's device is bound to this model and the operation fails."
                })
        status = True
        try:
            request.cursor.execute(update_model_sql, (is_public, model_id))
            request.conn.commit()
        except Exception:
            raise DCCAException("Fail to update the model")
    else:
        approved = False
        status = True
    try:
        request.cursor.execute(update_audit_sql, (approved, status, audit_id))
        request.conn.commit()
    except Exception:
        raise DCCAException("Fail to update audit")

    return jsonify({
        "status": "success",
        "message": "Operate successfully"
    })
