# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import json
from collections import OrderedDict

from flask import Blueprint, request, jsonify

from edgescale_pymodels.app_models import DccaSoftapp
from edgescale_pymodels.device_models import Host
from edgescale_pymodels.task_models import EsTask
from edgescale_pymodels.user_models import DccaUser
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.model_utils import ctx
from edgescale_pyutils.param_utils import empty_check, check_json
from edgescale_pyutils.view_utils import get_oemid, get_json
from model import K8S_HOST, K8S_PORT, MQTT_HOST, es_version, session
from model.ischema import *
from model.raw_sqls import *
from model.constants import *


task_bp = Blueprint("task", __name__)


@task_bp.route("", methods=["GET"])
def query_all_tasks():
    """
    Query tasks of all
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else 20
    offset = request.args.get('offset') if request.args.get('offset') else 0
    status = request.args.get('status')
    order_by = request.args.get('order_by') if request.args.get('order_by') else 'created_at'
    device_id = request.args.get('device_id')
    reverse = request.args.get('reverse')
    if reverse == "true":
        reverse = True
    elif reverse == "false":
        reverse = False
    else:
        reverse = True

    if order_by not in ['id', 'created_at']:
        return jsonify({
            'status': 'fail',
            'message': 'Invalid value of "order_by"'
        })

    if order_by not in ['id', 'created_at']:
        return jsonify({
            'status': 'fail',
            'message': 'Invalid value of "order_by"'
        })

    if status:
        status = status.lower().capitalize()
        if status not in TASK_STATUS_FILTER:
            return jsonify({
                'status': 'fail',
                'message': "Invalid status value, should be one of \"{0}\"".format(
                    ', '.join(map(str, list(TASK_STATUS_FILTER.keys()))))
            })

        _status = TASK_STATUS_FILTER[status]
    else:
        _status = None

    tasks, total = EsTask.query_all(status=_status, device_id=device_id, order_by=order_by,
                                    reverse=reverse, limit=limit, offset=offset, )

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = total
    results['items'] = []
    for task in tasks:
        results['items'].append(task.as_dict(schema=TaskSchema))

    return jsonify(results)


@task_bp.route("", methods=["POST"])
def create_task():
    """
    Create a task with payload
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    task_info = get_json(request).get("task", {})
    device_ids = task_info.get('device_ids')
    task_type = task_info.get('type')
    payloads = task_info.get('payload')

    devices = Host.query_in(device_ids)
    if len(devices) != len(device_ids):
        return jsonify({
            'status': 'fail',
            'message': 'Not authorized devices exist. Device not exist or cannot access',
            'not_authorized_devices': list(set(device_ids) - set([d.id for d in devices]))
        })

    try:
        inst_list = []
        if task_type == TASK_TYPE_NAMES[TASK_TYPE_APP]:
            unauthoried = EsTask.check_da_payload(payloads)
            if unauthoried:
                return jsonify({
                    'status': 'fail',
                    'message': 'Unauthorized application exists, not exist or cannot access. Do you have "version" in payload?',
                    'unauthorized': unauthoried
                })

            task = EsTask.create_da_task(payloads)
            task.started_at = datetime.utcnow()
            session.add(task)
            session.flush()
            for pl in payloads:
                softapp = DccaSoftapp.get(pl['softapp_id'])
                del pl['softapp_id']
                for device in devices:
                    inst = task.da_inst(device, softapp, pl)
                    session.add(inst)
                    inst_list.append(inst)

        elif task_type == TASK_TYPE_NAMES[TASK_TYPE_SOLUTION]:
            authed, solution = EsTask.check_ota_payload(payloads)
            if not authed:
                return jsonify({
                    'status': 'fail',
                    'message': 'Solution not exist or cannot access.'
                })

            task = EsTask.create_ota_task(payloads)
            task.started_at = datetime.utcnow()
            session.add(task)
            session.flush()
            for device in devices:
                inst = task.ota_inst(device, solution)
                session.add(inst)
                inst_list.append(inst)
        else:
            if not payloads:
                return jsonify({
                    'status': 'fail',
                    'message': 'payload is null.'
                })
            if not isinstance(payloads, dict):
                return jsonify({
                    'status': 'fail',
                    'message': 'payload is not dict.'
                })

            p = payloads.copy()
            p['device_ids'] = device_ids

            task = EsTask.create_common_task(TASK_TYPE_COMMON, p)
            task.started_at = datetime.utcnow()
            session.add(task)
            session.flush()
            for device in devices:
                inst = task.common_inst(device, payloads)
                session.add(inst)
                inst_list.append(inst)

            session.commit()

            data = []
            for inst in inst_list:
                data.append(dict({
                    'mid': inst.id,
                    'device': inst.device.name,
                    'issync': True,
                }, **payloads)
                )
            params = None

            deploy_url = RESOURCE_POST_TASK.format(dns=K8S_HOST, port=K8S_PORT, uid=uid)
            task.start(deploy_url, params, data=json.dumps(data))
        session.commit()

        for inst in inst_list:
            if inst.task.type == TASK_TYPE_APP:
                print('Start da task')
                try:
                    inst.start(K8S_HOST, K8S_PORT)
                    session.add(inst)
                except Exception:
                    session.rollback()
                else:
                    session.commit()
            elif inst.task.type == TASK_TYPE_SOLUTION:
                print('Start ota task')
                try:
                    inst.start(MQTT_HOST)
                    session.add(inst)
                except Exception:
                    session.rollback()
                else:
                    session.commit()

        results = OrderedDict()
        results['status'] = 'success'
        results['message'] = 'Success to create the task'
        results['task'] = task.as_dict(schema=TaskSchema)
        return jsonify(results)
    except Exception as e:
        raise DCCAException(str(e))


@task_bp.route("", methods=["DELETE"])
def remove_tasks_by_ids():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    task_ids_str = request.args.get('task_ids')
    empty_check(task_ids_str, error_message='The "task_ids" cannot be empty.')

    task_ids = task_ids_str.split(',')

    tasks = EsTask.query_in(task_ids)
    if len(tasks) < len(task_ids):
        return jsonify({
            'status': 'fail',
            'message': 'Not exist or cannot access',
            'unauthorized': list(set(task_ids) - set([t.id for t in tasks]))
        })

    try:
        data = []
        for task in tasks:
            task.logical_delete = True
            task.ended_at = datetime.utcnow()
            session.add(task)
            data.append(task.as_dict(schema=TaskSchema))
        session.commit()
    except Exception:
        raise DCCAException('Fail to remove task')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove tasks',
        'tasks': data
    })


@task_bp.route("/devices", methods=["GET"])
def query_all_task_devices():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else 100
    offset = request.args.get('offset') if request.args.get('offset') else 0

    device_set = set()
    tasks, total = EsTask.query_many(limit, offset)
    for task in tasks:
        devices = EsTask.query_task_devices(task)
        device_set = device_set | devices

    results = OrderedDict()
    results['total'] = total
    results['limit'] = limit
    results['offset'] = offset
    results['devices'] = [d.as_dict(schema=ShortDeviceSchema) for d in device_set]

    return jsonify(results)


def short_to_dict(t):
    if not t:
        return {}
    t = TaskTemltShort._make(t)
    d = {
        "id": t.id,
        "name": t.name,
        "desc": t.desc,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    }

    return d


def get_tasktmplt_list(cursor, user_id, limit, offset, name):
    name = '%%%s%%' % name
    r = {}
    cursor.execute(query_tasktmplt_number_sql, (user_id, name))
    l = cursor.fetchone()
    r['total'] = l[0] if (l and len(l) > 0) else 0
    r['limit'] = limit
    r['offset'] = offset
    r['items'] = []

    cursor.execute(query_tasktmplt_list, (user_id, name, limit, offset,))
    ts = cursor.fetchall()
    for t in ts:
        t = short_to_dict(t)
        r['items'].append(t)

    return r


@task_bp.route("/template", methods=["GET"])
def get_template_list():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') if request.args.get('limit') else 100
    offset = request.args.get('offset') if request.args.get('offset') else 0
    ftname = request.args.get('filter_name', "")
    try:
        r = get_tasktmplt_list(request.cursor, uid, limit, offset, ftname)
        return jsonify(r)
    except Exception as e:
        raise DCCAException(f"Error: get template list {str(e)}")


def full_to_dict(t):
    if not t:
        return {}
    t = TaskTemlt._make(t)
    d = {
        "id": t.id,
        "name": t.name,
        "desc": t.desc,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        d["body"] = json.loads(t.body)
    except Exception:
        d["body"] = t.body

    return d


def create_one_tasktmplt(cursor, user_id, name, desc, body):
    if "tr" in body:
        del body["tr"]

    if 'task' in body:
        body = body['task']

    if "payload" not in body:
        raise Exception("invalid body")

    body = json.dumps(body)
    cursor.execute(create_tasktmplt_sql, (name, desc, user_id, str(body),))
    t = cursor.fetchone()
    return full_to_dict(t)


def create_template_from_task(cursor, user_id, es_version, name, desc, taskid):
    ret = query_one_task_by_id(taskid)

    r = ret.get_json()
    if 'error' in r and r['error'] is True:
        if "message" in r:
            raise Exception("%s" % str(r["message"]))
    b = {}
    if "group_id" in r:
        b['type'] = r["type"]
        b['payload'] = r["payload"]
        b['group_id'] = r["group_id"]

    elif 'status_payload' in r:
        ds = []
        b['type'] = r["type"]
        b['payload'] = r["payload"]
        for d in r['status_payload']:
            ds.append(d['device_id'])
        b["device_ids"] = ds

    if len(b) < 1:
        raise Exception("%s" % str(r))
    return create_one_tasktmplt(cursor, user_id, name, desc, b)


@task_bp.route("/template", methods=["POST"])
def create_template():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    name = get_json(request).get('name', "")
    desc = get_json(request).get('desc', "")
    body = get_json(request).get('body', "")
    taskid = get_json(request).get('task_id', "")

    if len(name.strip()) < 1:
        raise DCCAException('Error: invalid  parameter for "name"')
    try:
        if len(body) > 0:
            t = create_one_tasktmplt(request.cursor, uid, name, desc, body)
            request.conn.commit()
        elif len(str(taskid)) > 0:
            t = create_template_from_task(request.cursor, uid, es_version, name, desc, taskid)
            request.conn.commit()
        else:
            raise DCCAException("body or task_id is required")

        if t and 'name' in t:
            r = {
                "status": "success",
                "message": "create template successfully"
            }
            r.update(t)
            return jsonify(r)
        else:
            raise DCCAException("%s" % str(t))

    except Exception as e:
        raise DCCAException(f"Error: create_template: {str(e)}")


def del_one_tasktmplt(cursor, user_id, tmpids):
    ids = [str(i) for i in tmpids]
    ids = tuple(ids)
    if len(ids) == 1:
        sql = "DELETE FROM dcca_task_template WHERE owner_id=%s AND id=%s RETURNING id;"
        cursor.execute(sql, (user_id, ids[0]))
    else:
        cursor.execute(delete_tasktmplt_sql % (user_id, ids,))

    t = cursor.fetchone()
    return t[0] if (t and len(t) > 0) else ""


@task_bp.route("/template", methods=["DELETE"])
def del_template():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    tid = get_json(request).get('ids')
    if len(tid) < 1 or not isinstance(tid, list):
        raise DCCAException('Error: invalid  parameter for "ids"')

    if len(tid[0]) > 40:
        raise DCCAException('Error: invalid id, too long')

    try:
        r = del_one_tasktmplt(request.cursor, uid, tid)
        request.conn.commit()
        if not r:
            raise DCCAException("%s seems not existing" % tid)
        r = {
            "status": "success",
            "message": "delete template successfully"
        }
        return jsonify(r)
    except Exception as e:
        raise DCCAException(f"Error: delete template: {str(e)}")


def device_to_dict(t):
    if not t:
        return {}
    t = Device._make(t)
    d = {
        "id": t.id,
        "name": t.name,
        "display_name": t.display_name,
        'model': {
            "model": t.model,
            "type": t.type,
            "platform": t.platform,
            "vendor": t.vendor
        }
    }

    return d


def full_image_path(username, image_name):
    return os.path.join(IMAGE_ROOT, username, image_name)


def app_to_dict(t):
    if not t:
        return {}
    t = App._make(t)
    d = {
        "id": t.id,
        "name": t.name,
        "display_name": t.display_name,
        "image": full_image_path(t.username, t.image),
        "description": t.description
    }

    return d


def get_one_tasktmplt_by_id(cursor, user_id, tmpid, tr=True):
    cursor.execute(query_one_tasktmplt_sql, (user_id, str(tmpid),))
    t = cursor.fetchone()
    r = full_to_dict(t)

    if not tr:
        return r

    if 'body' not in r:
        raise Exception("no such template or no permission")

    r0 = r['body']

    r["tr"] = {}
    if 'device_ids' in r0:
        ids = r0['device_ids'][:20]
        if len(ids) > 0 and type(ids[0]) == type(1):
            ids.append(1)
            ids_tup = tuple(ids)
            cursor.execute(query_device_list_sql % (user_id, ids_tup,))
            _ds = cursor.fetchall()
            ds = []
            ids.pop()
            for d in _ds:
                ds.append(device_to_dict(d))
            r["tr"]['device_ids'] = ds

    if 'payload' in r0:
        pds = r0['payload']
        r["tr"]['payload'] = []

        if type(pds) == type({}):
            r["tr"]['payload'].append(pds)

        elif type(pds) == type([]):
            for k, v in enumerate(pds):
                if v and 'application_id' in v:
                    cursor.execute(query_app_sql, (v["application_id"],))
                    t = cursor.fetchone()
                    a = app_to_dict(t)
                    if "version" in v:
                        a["version"] = v["version"]
                    else:
                        a["version"] = "latest"
                    r["tr"]['payload'].append(a)

                if v and "solution_id" in v:
                    r["tr"]['payload'].append(v)

    return r


@task_bp.route("/template/<tid>", methods=["GET"])
def get_one_template(tid):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if len(tid) < 5:
        raise DCCAException('Error: invalid  parameter for "id"')
    try:
        r = get_one_tasktmplt_by_id(request.cursor, uid, tid)
        return jsonify(r)
    except Exception as e:
        raise DCCAException(f"Error: get template: {str(e)}")


# @task_bp.route("/template/<tid>", methods=["POST"])
# def start_task_from_template_(tid):
#     uid, err = get_oemid(request=request)
#     if err is not None:
#         return jsonify(UNAUTH_RESULT)
#
#     try:
#         r = start_task_from_template(cursor, uid, es_version, tid)
#         conn.commit()
#         return r
#     except Exception as e:
#         raise DCCAException(f"Error: {str(e)}")


def update_one_tasktmplt(cursor, user_id, tmpid, name, desc, body):
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    v = "updated_at='%s'" % updated_at

    if name and len(name) > 0:
        v += ", name='%s'" % name

    if desc and len(desc) > 0:
        v += ''', "desc"='%s' ''' % desc

    if body and len(str(body)) > 10:
        org = get_one_tasktmplt_by_id(cursor, user_id, tmpid, tr=False)

        r0 = org['body']

        if "tr" in body:
            del body["tr"]

        if "tr" in r0:
            del r0["tr"]

        # update payload only
        if 'task' in body and "payload" in body["task"]:
            r0["payload"] = body["task"]["payload"]
        elif 'payload' in body:
            r0["payload"] = body["payload"]
        else:
            raise Exception("invalid body")

        if len(r0["payload"]) < 1:
            raise Exception("invalid body")

        org['body'] = r0

        v += ", body='%s'" % str(json.dumps(org['body']))

    sql_cmd = "UPDATE dcca_task_template "
    sql_cmd += "SET %s WHERE id='%s' RETURNING *;" % (v, str(tmpid))
    cursor.execute(sql_cmd)

    t = cursor.fetchone()
    return full_to_dict(t)


@task_bp.route("/template/<tid>", methods=["PUT"])
def update_template(tid):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    name = get_json(request).get('name')
    desc = get_json(request).get('desc')
    body = get_json(request).get('body')

    if len(tid) < 5:
        raise DCCAException('Error: invalid  parameter for "id"')

    try:
        t = update_one_tasktmplt(request.cursor, uid, tid, name, desc, body)
        request.conn.commit()
        if t and 'name' in t:
            r = {
                "status": "success",
                "message": "update template successfully"
            }
            r.update(t)
            return jsonify(r)
    except Exception as e:
        raise DCCAException(f"Error: update_template: {str(e)}")


@task_bp.route("/<task_id>", methods=["GET"])
def query_one_task_by_id(task_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(task_id, error_message='The "task_id" cannot be empty.')

    task = EsTask.query_by_id(task_id)
    if not task:
        return jsonify({
            'status': 'fail',
            'message': 'Task not exist or you are not permitted to access'
        })

    data = task.as_dict(schema=TaskSchema)
    data['status_payload'] = task.as_inst_dict()
    data['statistics'] = task.statistics()

    return jsonify(data)
