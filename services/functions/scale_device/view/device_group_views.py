# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import OrderedDict
from functools import reduce

from flask import Blueprint, request, jsonify

from edgescale_pymodels.app_models import DccaSoftapp
from edgescale_pymodels.base_model import session
from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pymodels.device_models import DccaDeviceGroup, Host, DccaAssHostModel
from edgescale_pymodels.solution_models import DccaModel
from edgescale_pymodels.task_models import EsTask
from edgescale_pymodels.user_models import DccaUser, DccaCustomer
from edgescale_pyutils.model_utils import ctx
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import empty_check, input_valid_check, check_json
from model import APPSERVER_HOST, APPSERVER_PORT, MQTT_HOST
from model.ischema import *
from utils import *

device_group_bp = Blueprint("device_group", __name__)


@device_group_bp.route("", methods=["GET"])
def query_device_groups():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') or DEFAULT_GROUP_LIMTI
    offset = request.args.get('offset') or DEFAULT_GROUP_OFFSET

    filter_name = request.args.get('filter_name')
    order_by = request.args.get('order_by')

    groups, size = DccaDeviceGroup.query_all(DeviceGroupSchema, order_column=order_by, uid=uid, filter_name=filter_name,
                                             limit=limit, offset=offset)

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = size
    results['groups'] = []

    for group in groups:
        results['groups'].append(group.as_dict(schema=DeviceGroupSchema))

    return jsonify(results)


@device_group_bp.route("", methods=["POST"])
def create_device_group():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    name = get_json(request).get('name')
    desc = get_json(request).get('description')
    customer = get_json(request).get('customer')

    if desc is None:
        desc = ''

    empty_check(name, error_message='Name cannot be empty')

    DccaDeviceGroup.is_name_taken(name, ctx.current_user)

    group = DccaDeviceGroup(name, description=desc, customer=customer)
    try:
        session.add(group)
        session.commit()
    except Exception:
        raise DCCAException('Fail to create device group')

    results = OrderedDict()
    results['status'] = 'success'
    results['message'] = 'Success to create a group'
    results['group'] = group.as_dict(schema=DeviceGroupSchema)

    return jsonify(results)


@device_group_bp.route("", methods=["DELETE"])
def batch_delete_device_group():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    group_ids = get_json(request).get('group_ids')

    empty_check(group_ids, error_message='The "group_ids" cannot be empty.')

    remove_fail_list = []
    remove_list = []
    results = OrderedDict()
    results['groups'] = OrderedDict()
    results['groups']['success'] = []
    results['groups']['fail'] = []

    for group_id in group_ids:
        group = DccaDeviceGroup.get_by_id(group_id, uid)
        if group:
            try:
                remove_list.append(group)
                group.remove()
                session.commit()
            except Exception as e:
                remove_fail_dict = {'id': group_id, 'message': e}
                remove_fail_list.append(remove_fail_dict)
                raise DCCAException('Fail to remove device group')
        else:
            message = 'Fail to remove device group'
            remove_fail_dict = {'id': group_id, 'message': message}
            remove_fail_list.append(remove_fail_dict)

    if len(remove_list) == 0:
        results['status'] = "fail"
        results['message'] = "Fail to remove device group"
        for group_fail in remove_fail_list:
            results['groups']['fail'].append(group_fail)
        results['groups']['fail_total'] = len(remove_fail_list)
    else:
        for group in remove_list:
            results['status'] = "success"
            results['message'] = "Success to remove group"
            results['groups']['success'].append(group.as_dict(schema=DeviceGroupBindSchema))
        results['groups']['success_total'] = len(remove_list)
        for group_fail in remove_fail_list:
            results['groups']['fail'].append(group_fail)
        results['groups']['fail_total'] = len(remove_fail_list)

    return jsonify(results)


def device_filter(cursor):
    devices = cursor.fetchall()

    results = []
    for d in devices:
        results.append(hashabledict({
            'id': d[0],
            'name': d[1]
        }))

    return results


def device_attr_filter(cursor, uid, limit, offset, items):
    limit = str(limit)
    offset = str(offset)

    def query_device(_type, _value):
        if _type == TYPE_COUNTRY:
            query_by_country_command = query_by_country_sql.format(user_id=uid, country=_value,
                                                                   limit=limit, offset=offset)
            cursor.execute(query_by_country_command)

            return device_filter(cursor)
        elif _type == TYPE_PLATFORM:
            query_by_platform_command = query_by_platform_sql.format(user_id=uid, platform=_value,
                                                                     limit=limit, offset=offset)
            cursor.execute(query_by_platform_command)

            return device_filter(cursor)
        else:
            return []

    results = []
    for item in items:
        _type = item.get('type')
        _value = item.get('value')
        if not _type or not _value:
            continue

        devices = query_device(_type, _value)
        results.append(set(devices))

    if results:
        return reduce(lambda x, y: x & y, results)  # Get the intersection of list
    else:
        return set()


@device_group_bp.route("/devices", methods=["POST"])
def device_save_to_group():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else DEFAULT_GROUP_LIMTI
    offset = request.args.get('offset') if request.args.get('offset') else DEFAULT_GROUP_OFFSET

    check_json(request)
    group_name = get_json(request).get("name")
    group_desc = get_json(request).get('description')
    customer_id = get_json(request).get('customer')
    bind_fail_list = []
    bind_list = []

    if group_desc is None:
        group_desc = ''

    customer = DccaCustomer.get_by_id(customer_id)
    if customer is None:
        customer_id = None
        session.commit()

    empty_check(group_name, error_message='Name cannot be empty')

    DccaDeviceGroup.is_name_taken(group_name, ctx.current_user)

    group = DccaDeviceGroup(group_name, description=group_desc, customer=customer_id)
    try:
        session.add(group)
    except Exception:
        raise DCCAException("Fail to create device group")
    devices = get_json(request).get('devices')

    if devices:
        for device in devices:
            device = Host.get_by_id(device)
            if device is None:
                bind_fail_dict = {'id': device, 'message': 'The device_id does not exist'}
                bind_fail_list.append(bind_fail_dict)
            else:
                if not device.has_group(group):
                    try:
                        device.groups.append(group)
                        session.add(device)
                        session.commit()
                        bind_list.append(device)
                    except Exception as e:
                        bind_fail_dict = {'id': device.id, 'message': e}
                        bind_fail_list.append(bind_fail_dict)
                        raise DCCAException('Fail to bind device to group')
                else:
                    message = 'This device already exists in the {} group, please do not add it repeatedly'.format(
                        group.name)
                    bind_fail_dict = {'id': device.id, 'message': message}
                    bind_fail_list.append(bind_fail_dict)
    else:
        intersection = get_json(request).get('intersection', False)

        results = []
        condition_items = get_json(request).get('by_condition')
        if 'by_condition' in get_json(request) and condition_items:
            if not any([x['value'] for x in condition_items]):
                devices_by_attr = set()
            else:
                devices_by_attr = device_attr_filter(request.cursor, uid, limit, offset, condition_items)
                results.append(devices_by_attr)
        else:
            devices_by_attr = set()

        if 'by_solution' in get_json(request) and get_json(request).get('by_solution'):
            solution_id = get_json(request).get('by_solution')

            devices_by_sol = device_solution_filter(request.cursor, uid, limit, offset, solution_id)
            results.append(devices_by_sol)

        else:
            devices_by_sol = set()

        if intersection:
            if results:
                devices = list(reduce(lambda x, y: x & y, results))
            else:
                devices = []
        else:
            devices = list(devices_by_attr | devices_by_sol)

        if len(devices) == 0:
            return jsonify({
                "status": "fail",
                "message": "The device that matches the search criteria is empty. Please re-enter."
            })

        for device in devices:
            device = Host.get_by_id(device['id'])
            if device is None:
                bind_fail_dict = {'id': device.id, 'message': 'The device_id does not exist'}
                bind_fail_list.append(bind_fail_dict)
            else:
                if not device.has_group(group):
                    try:
                        device.groups.append(group)
                        session.add(device)
                        session.commit()
                        bind_list.append(device)
                    except Exception as e:
                        bind_fail_dict = {'id': device.id, 'message': e}
                        bind_fail_list.append(bind_fail_dict)
                        raise DCCAException('Fail to bind device to group')
                else:
                    message = 'This device already exists in the {} group, please do not add it repeatedly'.format(
                        group.name)
                    bind_fail_dict = {'id': device.id, 'message': message}
                    bind_fail_list.append(bind_fail_dict)

    results = OrderedDict()
    if len(bind_list) == 0:
        results['status'] = "fail"
        results['message'] = "Fail to bind device to group"
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['devices'] = {}
    else:
        results['status'] = "success"
        results['message'] = "Success to add device to group"
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['devices'] = {}
        results['devices']['success'] = []
        results['devices']['success_total'] = len(bind_list)
        for device in bind_list:
            results['devices']['success'].append(device.as_dict(schema=DeviceIDSchema))
    results['devices']['fail'] = []
    results['devices']['fail_total'] = len(bind_fail_list)
    for device_fail in bind_fail_list:
        results['devices']['fail'].append(device_fail)

    return jsonify(results)


@device_group_bp.route("/model-devices", methods=["GET"])
def query_model_groups():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else 25
    offset = request.args.get('offset') if request.args.get('offset') else DEFAULT_GROUP_OFFSET
    models = DccaModel.get_all_model()

    result_model = {'type': 'model', 'results': []}
    for m in models:
        if not Host.model_has_device(m.id):
            continue
        name = "%d-%s-%s-%s-%s" % (m.id, m.model, m.type, m.platform, m.vendor)
        result_model['results'].append({"id": m.id, 'name': name})

    result_model['total'] = len(result_model['results'])
    result_model['limit'] = limit
    result_model['offset'] = offset
    r = [result_model]
    return jsonify(r)


def set_status(statistics, continent, status):
    if continent is None:
        continent = 'others'

    if status is None:
        if status not in statistics['by_continent']['others']:
            statistics['by_continent']['others'][status] = 1
        else:
            statistics['by_continent']['others'][status] += 1
    else:
        if status not in statistics['by_continent'][continent]:
            statistics['by_continent'][continent][status] = 1
        else:
            statistics['by_continent'][continent][status] += 1


@device_group_bp.route("/statistics", methods=["GET"])
def query_group_devices_statistics():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else DEFAULT_GROUP_LIMTI_STATISTICS
    offset = request.args.get('offset') if request.args.get('offset') else DEFAULT_GROUP_OFFSET

    filter_name = request.args.get('filter_name')
    empty_check(filter_name, error_message='Please pass in filter_name.')

    model_id = int(filter_name.split("-")[0])

    device_ids = DccaAssHostModel.get_model_deviceid(model_id)
    # print(device_ids)

    if not device_ids:
        return jsonify({})

    statistics = OrderedDict()
    statistics['by_continent'] = OrderedDict()
    statistics['by_continent']['others'] = OrderedDict()
    statistics['by_continent']['others']['total'] = 0
    statistics['by_status'] = OrderedDict()

    for device_id in device_ids:
        query_all_location_info_command = query_all_location_info_sql.format(limit=limit, offset=offset, user_id=uid,
                                                                             device_id=device_id[0])
        request.cursor.execute(query_all_location_info_command)
        location_items = request.cursor.fetchall()

        for loc_item in location_items:
            status = query_one_device_status(loc_item[1])
            loc_item = LocationItem._make(loc_item + (status,))
            continent = loc_item.continent
            status = loc_item.status
            if continent is None:
                statistics['by_continent']['others']['total'] += 1
                set_status(statistics, continent, status)
            elif continent not in statistics['by_continent']:
                statistics['by_continent'][continent] = {'total': 1}
                set_status(statistics, continent, status)
            else:
                statistics['by_continent'][continent]['total'] += 1
                set_status(statistics, continent, status)

            if status is None:
                statistics['by_status']['others'] += 1
            elif status not in statistics['by_status']:
                statistics['by_status'][status] = 1
            else:
                statistics['by_status'][status] += 1

    return jsonify(statistics)


@device_group_bp.route("/tasks", methods=["POST"])
def group_create_tasks():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    group_id = get_json(request).get('group_id')
    task_type = get_json(request).get('type')
    payloads = get_json(request).get('payload')
    # workaround it is not a uuid, group id
    if group_id and len(str(group_id)) < 32:
        device_list = DccaAssHostModel.get_model_deviceid(int(group_id))
    else:
        group = DccaDeviceGroup.get_by_id(group_id, uid)
        empty_check(group, error_message='The "group" is not accessable.')
        device_list = DccaDeviceGroup.query_bind_model_devices(group_id, uid)
    if not device_list or len(device_list) < 1:
        return jsonify({
            'status': 'fail',
            'message': 'There are no devices in this device group'
        })
    device_list = set(device_list)
    device_ids = [device_id[0] for device_id in device_list]

    devices = Host.query_in(device_ids)
    if len(devices) != len(device_ids):
        return jsonify({
            'status': 'fail',
            'message': 'Not authorized devices exist. Device not exist or cannot access',
            'not_authorized_devices': list(set(device_ids) - set([d.id for d in devices]))
        })

    if task_type not in list(TASK_TYPE_NAMES.values()):
        return jsonify({
            'status': 'fail',
            'message': 'No such kind of task'
        })

    try:
        inst_list = []
        if task_type == TASK_TYPE_NAMES[TASK_TYPE_APP]:
            unauthoried = EsTask.check_da_payload(payloads)
            if unauthoried:
                return jsonify({
                    'status': 'fail',
                    'message': 'Unauthorized application exists, not exist or cannot access.',
                    'unauthorized': unauthoried
                })

            task = EsTask.create_da_task(payloads)
            session.add(task)
            session.flush()
            for pl in payloads:
                softapp = DccaSoftapp.get(pl['softapp_id'])
                del pl['softapp_id']
                for device in devices:
                    inst = task.da_inst(device, softapp, pl)
                    session.add(inst)
                    inst_list.append(inst)
            session.commit()
        elif task_type == TASK_TYPE_NAMES[TASK_TYPE_SOLUTION]:
            authed, solution = EsTask.check_ota_payload(payloads)
            if not authed:
                return jsonify({
                    'status': 'fail',
                    'message': 'Solution not exist or cannot access.'
                })

            task = EsTask.create_ota_task(payloads)
            session.add(task)
            session.flush()
            for device in devices:
                inst = task.ota_inst(device, solution)
                session.add(inst)
                inst_list.append(inst)
            session.commit()
        else:
            return jsonify({
                'status': 'fail',
                'message': 'No such kind of task'
            })

        try:
            for inst in inst_list:
                if inst.task.type == TASK_TYPE_APP:
                    print(('Start da task: ', inst))
                    inst.start(APPSERVER_HOST, APPSERVER_PORT)
                elif inst.task.type == TASK_TYPE_SOLUTION:
                    print('Start ota task')
                    inst.start(MQTT_HOST)
        except Exception:
            import traceback
            traceback.print_exc()
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


@device_group_bp.route("/<group_id>", methods=["GET"])
def query_one_group(group_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else DEFAULT_GROUP_LIMTI
    offset = request.args.get('offset') if request.args.get('offset') else DEFAULT_GROUP_OFFSET

    empty_check(group_id, error_message='The "group_id" cannot be empty.')
    results = OrderedDict()

    # workaround it is not a uuid, group id
    if group_id and len(str(group_id)) < 32:
        devices_group_list = DccaAssHostModel.get_model_deviceid(int(group_id))

        r = DccaModel.get_by_id(int(group_id))
        if not r:
            raise Exception("%s: group or model not found" % (str(group_id)))

        results['id'] = r.id
        name = "%s-%s-%s-%s" % (r.model, r.type, r.platform, r.vendor)
        results['name'] = name
        results["description"] = "%s: model group" % name

    else:
        group = DccaDeviceGroup.get_by_id(group_id, uid)
        empty_check(group, error_message='The "group" is not accessable.')
        devices_group_list = group.query_bind_devices(limit=limit, offset=offset)

        results['id'] = group_id
        results["name"] = group.name
        results["description"] = group.desc

    results["device"] = OrderedDict()
    results["device"]['limit'] = limit
    results["device"]['offset'] = offset
    results['devices'] = []
    total = 0

    for device_group in devices_group_list:
        device_id = device_group[0]
        device = Host.get_id(device_id)
        if device:
            model_id = Host.get_model_id(device_id)
            devices = device.as_dict(schema=DeviceSchema)
            devices['status'] = query_one_device_status(devices['name'])
            total += 1
            results['devices'].append(devices)
            if model_id[0]:
                model = DccaModel.get_by_id(model_id)
                devices['model'] = model.as_dict(schema=ModelSchema)
    results['device']['total'] = total

    return jsonify(results)


@device_group_bp.route("/<group_id>", methods=["PUT"])
def modify_one_group(group_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(group_id, error_message='The "group_id" cannot be empty.')

    check_json(request)
    name = get_json(request).get('name')
    input_valid_check(name, error_message='Invalid characters in name.')

    group = DccaDeviceGroup.get_by_id(group_id, uid)

    empty_check(group, error_message='The "group" is not accessable.')

    desc = get_json(request).get('description')

    if not name and not desc:
        return jsonify({
            'status': 'fail',
            'message': 'Empty parameters, not modified'
        })

    if name:
        group.name = name

    if desc:
        group.desc = desc
    elif desc == '':
        group.desc = ''

    group.updated_at = datetime.utcnow()

    try:
        session.add(group)
        session.commit()
    except Exception:
        raise DCCAException('Fail to update group')

    results = OrderedDict()
    results['status'] = 'success'
    results['message'] = 'Success to update group'
    results['group'] = group.as_dict(schema=DeviceGroupSchema)

    return jsonify(results)


@device_group_bp.route("/<group_id>", methods=["DELETE"])
def delete_device_group(group_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(group_id, error_message='The "group_id" cannot be empty.')

    group = DccaDeviceGroup.get_by_id(group_id, uid)
    empty_check(group, error_message='The "group" is not accessable.')

    try:
        group.remove()
        session.commit()
    except Exception:
        raise DCCAException('Fail to remove device group')

    results = OrderedDict()
    results['status'] = 'success'
    results['message'] = 'Success to remove group'
    results['group'] = group.as_dict(schema=DeviceGroupSchema)

    return jsonify(results)


@device_group_bp.route("/<group_id>/devices", methods=["POST"])
def batch_bind_device(group_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(group_id, error_message='The "group_id" cannot be empty.')

    check_json(request)
    device_ids = get_json(request).get("devices")
    empty_check(device_ids, error_message='The "device_ids" cannot be empty')

    if len(device_ids) > 50:
        return jsonify({
            "status": "fail",
            "message": "Exceed max limit which is 50 for each request"
        })

    group = DccaDeviceGroup.get_by_id(group_id, uid)

    if group is None:
        return jsonify({
            'status': 'fail',
            'message': "The group_id does not exist"
        })

    bind_fail_list = []
    bind_list = []
    for device_id in device_ids:
        device = Host.get_by_id(device_id)
        if device is None:
            bind_fail_dict = {'id': device_id, 'message': 'The device_id does not exist'}
            bind_fail_list.append(bind_fail_dict)
        else:
            if not device.has_group(group):
                try:
                    device.groups.append(group)
                    session.add(device)
                    session.commit()
                    bind_list.append(device)
                except Exception as e:
                    bind_fail_dict = {'id': device_id, 'message': e}
                    bind_fail_list.append(bind_fail_dict)
                    raise DCCAException('Fail to bind device to group')
            else:
                message = 'This device already exists in the {} group, please do not add it repeatedly'.format(
                    group.name)
                bind_fail_dict = {'id': device_id, 'message': message}
                bind_fail_list.append(bind_fail_dict)

    results = OrderedDict()
    if len(bind_list) == 0:
        results['status'] = "fail"
        results['message'] = "Fail to bind device to group"
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['devices'] = {}
    else:
        results['status'] = "success"
        results['message'] = "Success to add device to group"
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['devices'] = {}
        results['devices']['success'] = []
        results['devices']['success_total'] = len(bind_list)
        for device in bind_list:
            results['devices']['success'].append(device.as_dict(schema=DeviceIDSchema))
    results['devices']['fail'] = []
    results['devices']['fail_total'] = len(bind_fail_list)
    for device_fail in bind_fail_list:
        results['devices']['fail'].append(device_fail)

    return jsonify(results)


@device_group_bp.route("/<group_id>/devices", methods=["DELETE"])
def remove_device_from_group(group_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(group_id, error_message='The "group_id" cannot be empty.')

    check_json(request)
    device_ids = get_json(request).get('devices')
    empty_check(device_ids, error_message='The "device_ids" cannot be empty')

    group = DccaDeviceGroup.get_by_id(group_id, uid)

    if group is None:
        return jsonify({
            'status': 'fail',
            'message': "The group_id does not exist"
        })

    remove_fail_list = []
    remove_list = []
    for device_id in device_ids:
        device = Host.get_by_id(device_id)
        if device is None:
            bind_fail_dict = {'id': device_id, 'message': 'The device_id does not exist'}
            remove_fail_list.append(bind_fail_dict)
        else:
            if device.has_group(group):
                try:
                    group.devices.remove(device)
                    session.commit()
                    remove_list.append(device)
                except Exception as e:
                    bind_fail_dict = {'id': device_id, 'message': e}
                    remove_fail_list.append(bind_fail_dict)
                    raise DCCAException('Fail to bind device to group')
            else:
                message = 'This device already exists in the {} group, please do not add it repeatedly'.format(
                    group.name)
                bind_fail_dict = {'id': device_id, 'message': message}
                remove_fail_list.append(bind_fail_dict)

    results = OrderedDict()
    if len(remove_list) == 0:
        results['status'] = "fail"
        results['message'] = "Fail to unbind device from group"
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['devices'] = {}
    else:
        results['status'] = "success"
        results['message'] = "Success to remove device from group"
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['devices'] = {}
        results['devices']['success'] = []
        results['devices']['success_total'] = len(remove_list)
        for device in remove_list:
            results['devices']['success'].append(device.as_dict(schema=DeviceIDSchema))
    results['devices']['fail'] = []
    results['devices']['fail_total'] = len(remove_fail_list)
    for device_fail in remove_fail_list:
        results['devices']['fail'].append(device_fail)

    return jsonify(results)


@device_group_bp.route("/<group_id>/devices/<device_id>", methods=["POST"])
def bind_device_to_group(group_id, device_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    empty_check(group_id, error_message='The "group_id" cannot be empty.')
    empty_check(device_id, error_message='The "device_id" cannot be empty')

    group = DccaDeviceGroup.get_by_id(group_id, uid)

    if group is None:
        return jsonify({
            'status': 'fail',
            'message': "The group_id does not exist"
        })

    device = Host.get_by_id(device_id)
    if device is None:
        return jsonify({
            'status': 'fail',
            'message': "The device_id does not exist"
        })

    results = OrderedDict()

    if not device.has_group(group):
        try:
            device.groups.append(group)
            session.add(device)
            session.commit()
        except Exception:
            raise DCCAException('Fail to bind device to group')

        results['status'] = 'success'
        results['message'] = 'Success to add device to group'
        results['group'] = group.as_dict(schema=DeviceGroupBindSchema)
        results['device'] = device.as_dict(schema=DeviceIDSchema)
    else:
        results['status'] = 'fail'
        results['message'] = 'This device already exists in the {} group, please do not add it repeatedly'.format(group.name)

    return jsonify(results)
