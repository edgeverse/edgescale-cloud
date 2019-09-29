# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import copy
import os
import json
import uuid
from collections import OrderedDict
from functools import reduce

import boto3
import geoip2.database
import requests
from geoip2.errors import AddressNotFoundError
from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pymodels.device_models import Host, ScaleSubdevReg
from edgescale_pymodels.task_models import EsTaskOtaInst
from edgescale_pymodels.user_models import DccaUser, DccaCustomer, DccaUserLimit
from edgescale_pyutils.model_utils import ctx
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.common_utils import format_time
from edgescale_pyutils.param_utils import empty_check, check_json
from model import IS_DEBUG, SHORT_REST_API_ID, MQTT_HOST, S3_LOG_URL, DEVICE_TABLE, MQTT_LOCAL_HOST, \
    MQTT_MGMT_PASS, MQTT_MGMT_USER, REDIS_KEY_CREATE_DEVICE_FORMAT, API_URI, MQTT_URI, docker_content_trust_server
from model import session
from utils import *


device_bp = Blueprint("device", __name__)


@device_bp.route("", methods=["GET"])
def get_all():
    """
    Query all the users' devices
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') if request.args.get('limit') else 20
    offset = request.args.get('offset') if request.args.get('offset') else 0
    order_by = request.args.get('order_by') if request.args.get('order_by') else 'created_at'
    order_type = request.args.get('orderType') if request.args.get('orderType') else 'desc'
    display_name = request.args.get('filter_name')
    location = request.args.get('filter_location')
    platform = request.args.get('filter_platform')
    device_tag = request.args.get('filter_tag')
    model_id = request.args.get('filter_model')

    total, datas = Host.query_all_devices_by_filter(uid=uid, display_name=display_name,
                                                    location=location, platform=platform,
                                                    device_tag=device_tag, order_by=order_by, model_id=model_id,
                                                    order_type=order_type, limit=limit, offset=offset)
    results = OrderedDict()
    results['total'] = total
    results['order_type'] = order_type
    results['order_by'] = order_by
    results['limit'] = limit
    results['offset'] = offset

    results['results'] = []

    sub_devices = ScaleSubdevReg.query_by_hosts_ids([d.Host.id for d in datas])

    for data in datas:
        device_info = OrderedDict()
        device_info['id'] = data.Host.id
        device_info['name'] = data.Host.name
        device_info['created_at'] = format_time(data.Host.created_at)
        device_info['display_name'] = data.Host.display_name
        item = data.Host.lifecycle
        device_info['lifecycle'] = status_list[item - 1] if item else None

        device_info['mode'] = OrderedDict()
        device_info['mode']['model'] = data.Host.model.model
        device_info['mode']['type'] = data.Host.model.type
        device_info['mode']['platform'] = data.Host.model.platform
        device_info['mode']['vendor'] = data.Host.model.vendor

        device_info['tags'] = [{'id': t.id, 'name': t.name} for t in data.Host.tags]
        device_status = query_one_device_status(data.Host.name)
        device_info.update(device_status)

        device_info['has_sub'] = False
        for s in sub_devices:
            if s.hostid == data.Host.id:
                device_info['has_sub'] = True

        results['results'].append(device_info)

        data.Host.redis_client = redis_client
        device_info.update(data.Host.status())

    return jsonify(results)


@device_bp.route("", methods=["POST"])
def register_one_device_v2():
    """
    Register one device (Create one device).
    No foreman API
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    device = get_json(request).get('device', {})
    fuid = device.get('fuid')
    model_id = device.get('model_id')
    display_name = device.get('display_name')

    # Check parameters
    if not fuid:
        return jsonify({
            'status': 'fail',
            'message': '"UID" cannot be empty.'
        })

    if not model_id:
        return jsonify({
            'status': 'fail',
            'message': '"model_id" cannot be empty.'
        })

    # Query max limit of device
    exceed_flag, max_limit = exceed_max_device_number(request.cursor, redis_client, user_id=uid)
    if exceed_flag:
        return jsonify({
            'status': 'fail',
            'message': 'Exceed the max limit number of devices. '
                       'You can only create at most {} devices.'.format(max_limit)
        })

    # Check if exceed max limit of binding model
    if exceed_max_model_number(request.cursor, redis_client, user_id=uid, model_id=model_id):
        return jsonify({
            'status': 'fail',
            'message': 'You have exceeded the limitation that can bind device to this kind of model'
        })

    request.cursor.execute(query_model_by_id_sql, (model_id,))
    mode = request.cursor.fetchone()
    if not mode:
        return jsonify({
            'status': 'fail',
            'message': 'The model given not exists'
        })

    mode_names = list(mode[1:-2])
    mode_names.insert(0, fuid)
    device_name = '.'.join(str(v) for v in mode_names)
    if is_oem_user(request.cursor, uid):
        oem_uid = uid
    else:
        # common user, use default
        oem_uid = 0

    if len(device_name) > 64:
        return jsonify({
            'status': 'fail',
            'message': 'device name is too long:' + device_name
        })

    try:
        lifecycle = CREATED
        request.cursor.execute(create_device_sql, (device_name, device_name, uid, model_id, display_name, lifecycle, oem_uid))
        device_id = request.cursor.fetchone()[0]
    except Exception as e:
        if IS_DEBUG:
            print(e)
        # if hasattr(e, 'pgcode') and e.pgcode == '23505':
        #     check_code = CODE_DUPLICATE

        raise DCCAException('Fail to create device')

    # Bound the device to the model TODO remove later
    try:
        request.cursor.execute(insert_ass_device_model_sql, (device_id, model_id,))
    except Exception:
        raise DCCAException('Fail to update device model')

    # Make the user the owner of the device
    try:
        request.cursor.execute(create_device_owner_sql, (uid, device_id,))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to make owner of device')
    else:
        make_record_deploy_times(redis_client, SHORT_REST_API_ID, user_id=uid, redis_key=REDIS_KEY_CREATE_DEVICE_FORMAT)

    incr_create_device_counter(redis_client, uid)
    incr_user_bind_model_counter(redis_client, uid, model_id)

    ret = OrderedDict()
    ret['status'] = 'success'
    ret['message'] = 'Success to create device.'

    ret['device'] = OrderedDict()
    ret['device']['id'] = device_id
    ret['device']['name'] = device_name
    ret['device']['certname'] = device_name

    return jsonify(ret)


@device_bp.route("", methods=["PUT"])
def change_device_status():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    device_id = get_json(request).get("device_id")
    status = get_json(request).get("action")

    status = DEVICE_STATUS.get(status)

    try:
        request.cursor.execute(change_device_status_sql, (status, device_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to change device status')

    return jsonify({
        "status": "success",
        "message": "Success to change device status"
    })


@device_bp.route("/claim", methods=["POST"])
def bind_device_owner_view():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    fuid = get_json(request).get('fuid')
    oemuid = get_json(request).get('oemuid')
    # mptag = get_json(request).get('mptag')

    def get_device_name():
        try:
            from model import mft_pool
        except Exception:
            mft_pool = None

        if not mft_pool:
            raise DCCAException("Database Error.")

        mftconn = mft_pool.connection()
        fmtcursor = mftconn.cursor()
        try:
            fmtcursor.execute('SELECT D.id, M.device_model, M.type, M.platform, M.vendor\
                                FROM devices AS D LEFT JOIN device_models AS M ON D.model_id=M.model_id\
                                WHERE D.fuid=%s AND D.oem_uid=%s;', (fuid, oemuid[8:]))
            r = fmtcursor.fetchone()
            if r:
                return '.'.join(r)

        except Exception as e:
            raise DCCAException(str(e))
        finally:
            mftconn.close() if mftconn else None

    device_name = get_device_name()

    if device_name and len(device_name) > 0:
        pass
    else:
        raise DCCAException('device is not found')

    if bind_device_owner(request.cursor, device_name, uid):
        pass
    else:
        raise DCCAException('device is not found or already bound')
    request.conn.commit()
    return jsonify({
        'status': 'success',
        'message': 'Success to bind device: %s' % device_name
    })


def device_blurred_filter(cursor, uid, limit, offset, tag_ids):
    query_device_blurred_by_tag_sql = 'SELECT DISTINCT D.id, D.name' \
                                      ' FROM hosts AS D'
    # ' LEFT JOIN dcca_ass_user_device AS AUD' \
    # ' ON D.id=AUD.device_id'

    where = ''
    for index, tag_id in enumerate(tag_ids):
        query_device_blurred_by_tag_sql += ' LEFT JOIN dcca_ass_device_tag AS T{}'.format(index)
        query_device_blurred_by_tag_sql += ' ON D.id=T{}.device_id'.format(index)
        where += ' AND T{}.tag_id={}'.format(index, tag_id)

    query_device_blurred_by_tag_sql += ' WHERE'
    query_device_blurred_by_tag_sql += ' D.owner_id={user_id}'.format(user_id=uid)
    query_device_blurred_by_tag_sql += where
    query_device_blurred_by_tag_sql += ' LIMIT {limit} OFFSET {offset}'.format(limit=str(limit), offset=str(offset))

    cursor.execute(query_device_blurred_by_tag_sql)
    devices = cursor.fetchall()

    results = []
    for device in devices:
        d = ShortDevice._make(device)
        results.append(hashabledict({
            'id': d.id,
            'name': d.name
        }))

    return set(results)


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
            cursor.execute(query_by_country_sql_v2, (uid, _value, limit, offset))

            return device_filter(cursor)
        elif _type == TYPE_PLATFORM:
            cursor.execute(query_by_platform_sql_v2, (uid, _value, limit, offset))

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


@device_bp.route("/filter", methods=["POST"])
def query_by_multiple_conditions():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    bata_json = get_json(request)
    limit = bata_json.get('limit') if bata_json.get('limit') else 10000
    offset = bata_json.get('offset') if bata_json.get('offset') else 0

    intersection = bata_json.get('intersection', False)

    results = []
    tag_ids = bata_json.get('by_tag')
    if 'by_tag' in bata_json and tag_ids:
        devices_by_tag = device_blurred_filter(request.cursor, uid, limit, offset, tag_ids)
        results.append(devices_by_tag)
    else:
        by_tag_flag = False
        devices_by_tag = set()

    condition_items = bata_json.get('by_condition')
    if 'by_condition' in bata_json and condition_items:
        if not any([x['value'] for x in condition_items]):
            devices_by_attr = set()
        else:
            devices_by_attr = device_attr_filter(request.cursor, uid, limit, offset, condition_items)
            results.append(devices_by_attr)
    else:
        devices_by_attr = set()

    if 'by_solution' in bata_json and bata_json.get('by_solution'):
        solution_id = bata_json.get('by_solution')

        devices_by_sol = device_solution_filter(request.cursor, uid, limit, offset, solution_id)
        results.append(devices_by_sol)

    else:
        devices_by_sol = set()

    if intersection:
        if results:
            return jsonify(list(reduce(lambda x, y: x & y, results)))
        else:
            return jsonify([])
    else:
        return jsonify(list(devices_by_tag | devices_by_attr | devices_by_sol))  # TODO


@device_bp.route("/filter/attributes", methods=["GET"])
def query_attribute_list():
    """
    Query the device attribute list
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    # cursor.execute(query_device_attrs_command)
    # attributes = cursor.fetchall()
    #
    # results = {'attributes': []}
    # for attr in attributes:
    #     attr = DeviceAttr._make(attr)
    #     results['attributes'].append(attr._asdict())
    # return jsonify(results)

    return jsonify({'attributes': [{'id': 1, 'name': 'location'},
                                   {'id': 2, 'name': 'platform'}]})


@device_bp.route("/filter/attributes/name", methods=["GET"])
def query_by_attr():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    attr_id = request.args.get('attr_id')

    def attributes_filter(cursor, attr_type):
        items = cursor.fetchall()
        results = {
            'type': attr_type,
            'values': []
        }

        for item in items:
            results['values'].append(item[0])

        return results

    if attr_id == "1":
        # query_location_command = query_location_sql.format(user_id=uid)
        request.cursor.execute(query_location_sql_v2, (uid, ))

        return jsonify(attributes_filter(request.cursor, TYPE_COUNTRY))
    elif attr_id == "2":
        request.cursor.execute(query_platform_command)

        return jsonify(attributes_filter(request.cursor, TYPE_PLATFORM))
    else:
        return jsonify({
            'status': 'fail',
            'message': 'Not support attribute'
        })


# @device_bp.route("", methods=["GET"])
def query_by_value():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    _type = request.args.get('type')
    value = request.args.get('value')

    limit = request.args.get('limit') if request.args.get('limit') else 1000
    offset = request.args.get('offset') if request.args.get('offset') else 0

    if isinstance(limit, str) and not limit.isdigit():
        return jsonify({
            'status': 'fail',
            'message': 'Invalid limit, must be digit'
        })
    elif isinstance(offset, str) and not offset.isdigit():
        return jsonify({
            'status': 'fail',
            'message': 'Invalid offset, must be digit'
        })

    if _type == TYPE_COUNTRY:
        request.cursor.execute(query_by_country_sql_v2, (uid, value, limit, offset))

        return jsonify(device_filter(request.cursor))
    elif _type == TYPE_PLATFORM:
        request.cursor.execute(query_by_platform_sql_v2, (uid, value, limit, offset))

        return jsonify(device_filter(request.cursor))


# @device_bp.route("", methods=["GET"])
def query_multiple_by_values():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    items = request.args.get('items')
    limit = request.args.get('limit') if request.args.get('limit') else 10000
    offset = request.args.get('offset') if request.args.get('offset') else 0

    def query_device(_type, _value):
        if _type == TYPE_COUNTRY:
            request.cursor.execute(query_by_country_sql_v2, (uid, _value, limit, offset))

            return device_filter(request.cursor)
        elif _type == TYPE_PLATFORM:
            request.cursor.execute(query_by_platform_sql_v2, (uid, _value, limit, offset))

            return device_filter(request.cursor)
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

    return jsonify(reduce(lambda x, y: x & y, results))


@device_bp.route("/locations", methods=["GET"])
def query_device_locations():
    """
    Query device location by given device_ids.
    Original "wrapper_device_info:query_device_info"
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    device_ids_str = request.args.get('device_ids')

    # Check the parameters
    if ' ' in device_ids_str:
        return jsonify({
            'status': 'fail',
            'message': 'Cannot contain whitespace in device ids parameter'
        })

    device_ids = device_ids_str.split(',')

    if not is_device_owner(request.cursor, user_id=uid, device_ids=device_ids):
        return jsonify({
            'status': 'fail',
            'message': 'One or more unauthorized devices exist'
        })

    device_info = query_device_location(request.cursor, user_id=uid, device_ids=device_ids)

    results = []
    for info in device_info:
        info = DeviceLocation._make(info)
        device_msg = info._asdict()
        status = query_one_device_status(info.name)
        device_msg.update(status)
        results.append(device_msg)

    return jsonify(results)


@device_bp.route("/logs", methods=["GET"])
def get_device_logs():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    name = request.args.get('device_name')
    log_type = request.args.get('log_type')
    empty_check(name, error_message='The "device_name" cannot be empty.')

    payload = {
        'action': 'uploadlog',
        'type': log_type
    }

    EsTaskOtaInst.publish(MQTT_HOST, payload, name=name)
    presigned_url = S3_LOG_URL + "/signer?username={0}&objectname={1}&type=text".format(log_type,name)
    return jsonify({
        "state":"success",
        "url": presigned_url
    })


@device_bp.route("/logs/signer", methods=["GET"])
def get_logs_signer():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    device_id = request.args.get('device_id')
    logname = request.args.get('logname')

    presigned_url = S3_LOG_URL + "/signer?username={0}&objectname={1}&type=text".format(logname,device_id)
    return jsonify({
        "state":"success",
        "url": presigned_url
    })


@device_bp.route("/statistics", methods=["GET"])
def query_devices_statistics_v2():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    status_list = [
        {"status": "created", "number": 0},
        {"status": "new", "number": 0},
        {"status": "authenticated", "number": 0},
        {"status": "active", "number": 0},
        {"status": "inactive", "number": 0},
        {"status": "retired", "number": 0}
    ]
    num_list = [1, 2, 3, 4, 5, 6]
    for status in num_list:
        request.cursor.execute(count_lifecycle_status_sql, (uid, status))
        num = request.cursor.fetchone()[0]
        status_list[status - 1]["number"] = int(num)

    return jsonify(status_list)


@device_bp.route("/operation", methods=["GET"])
def execute_operation():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    device_name = str(request.args.get("device_id", ''))
    device_id = str(request.args.get("device_id", '')).split('.')[0]

    try:
        resp = boto3.client('dynamodb').get_item(
            TableName=DEVICE_TABLE,
            Key={
                'deviceId': {"S": device_id},
            }
        )
    except ClientError as e:
        return jsonify({"error": e.response['Error']['Message']})

    if len(str(request.args("device_id", "")).split(".")) < 5:
        topic = "edgescale/device/" + device_id + "." + resp["Item"]["info"]["M"]["model"]["S"]
        if os.getenv('mqtopic') == 'v1':
            topic = "device/" + device_id + "." + resp["Item"]["info"]["M"]["model"]["S"]

        # client_id = device_id + "." + resp["Item"]["info"]["M"]["model"]["S"]
    else:
        topic = "edgescale/device/" + str(request.args("device_id", ''))
        if os.getenv('mqtopic') == 'v1':
            topic = "device/" + str(request.args("device_id", ''))
        # client_id = str(request.args("device_id", ''))

    execute_action = ''
    operation_method = request.args.get("action")
    device_lifecycle = NEW

    request.cursor.execute(query_device_current_status, (device_name,))
    current_status = request.cursor.fetchone()[0]

    if operation_method == "reset":

        if current_status == RETIRED:
            return jsonify({"status": "fail", "message": "fail to reset"})

        try:
            request.cursor.execute(update_device_lifecycle_by_device_name, (device_lifecycle, device_name))
            request.conn.commit()
            execute_action = '{"action": "factory_reset"}'
        except ClientError as e:
            request.conn.rollback()
            return jsonify({"error": e.response['Error']['Message']})

    elif operation_method == "reboot":
        if current_status == RETIRED:
            return jsonify({"status": "fail", "message": "fail to reboot"})
        execute_action = {
                'action': 'device_reboot',
                'mid': str(uuid.uuid4()),
         }

    try:
        cc = {
            "topic": topic,
            "payload": execute_action,
            "qos": 2,
            "retain": False,
            "client_id": "iot-hub-lambda"
        }
        requests.post(MQTT_LOCAL_HOST + "/api/v3/mqtt/publish", data=json.dumps(cc),
                      auth=(MQTT_MGMT_USER, MQTT_MGMT_PASS))
        return jsonify({"status": 'success', "message": "operation successfully"})
    except ClientError as e:
        return jsonify({"error": e.response['Error']['Message']})


@device_bp.route("/positions", methods=["GET"])
def query_all_devices_position():
    """
    Origin from wrapper_device_locations:query_all_devices
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') if request.args.get('limit') else 5000
    offset = request.args.get('offset') if request.args.get('offset') else 0

    if uid in [45, '45']:
        request.cursor.execute(query_all_positions_sql, (limit, offset))
    else:
        request.cursor.execute(query_device_positions_sql, (uid, limit, offset))

    positions = request.cursor.fetchall()

    results = {}
    for pos in positions:
        pos = Position._make(pos)

        lat_lng = '%f,%f' % (pos.lat or 0.0, pos.lng or 0.0)
        if lat_lng not in results:
            results[lat_lng] = {
                'lat': pos.lat,
                'lng': pos.lng,
                'device_ids': [pos.device_id]
            }
        else:
            results[lat_lng]['device_ids'].append(pos.device_id)

    return jsonify(results)


@device_bp.route("/positions", methods=["POST"])
def save_device_position():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    ip_address = get_json(request).get('ip', "127.0.0.1")
    device_name = get_json(request).get('device_name')

    query_device_by_name_cmd = query_device_by_name_sql.format(device_name=device_name)
    request.cursor.execute(query_device_by_name_cmd)
    device = request.cursor.fetchone()
    if device is None:
        return jsonify({
            'status': 'fail',
            'message': 'Device not exist or you do not have the permission'
        })

    DeviceInfo = namedtuple('DeviceInfo', ['id', 'position_id'])
    device = DeviceInfo._make(device)
    device_id = device.id
    position_id = device.position_id

    _dirname = os.path.dirname(os.path.realpath(__file__))
    resp = geoip2.database.Reader(os.path.join(os.path.dirname(_dirname), 'GeoLite2-City.mmdb'))
    try:
        city = resp.city(ip_address)
    except AddressNotFoundError:
        if position_id is None:
            request.cursor.execute(create_device_position_sql, (device_id, ip_address, None, None, None, None))
        else:
            request.cursor.execute(update_device_position_sql, (ip_address, None, None, None, None, device_id))
    else:
        city_name = city.city.name
        continent = city.continent.code
        country = city.country.name
        latitude = city.location.latitude
        longitude = city.location.longitude

        city_country_name = '{}/{}'.format(city_name, country)

        query_location_cmd = query_location_sql.format(name=city_country_name)
        request.cursor.execute(query_location_cmd)
        location = request.cursor.fetchone()
        if location is None:
            create_location_cmd = create_location_sql.format(name=city_country_name)
            try:
                request.cursor.execute(create_location_cmd)
                location_id = request.cursor.fetchone()[0]
            except Exception:
                raise DCCAException('Fail to create location')
        else:
            location_id = location[0]

        query_continent_cmd = query_continent_sql.format(continent=continent)
        request.cursor.execute(query_continent_cmd)

        continent_id = request.cursor.fetchone()[0]

        if position_id is None:
            request.cursor.execute(create_device_position_sql,
                                   (device_id, ip_address, location_id, continent_id, latitude, longitude))
        else:
            request.cursor.execute(update_device_position_sql,
                                   (ip_address, location_id, continent_id, latitude, longitude, device_id))
    finally:
        request.conn.commit()
    return jsonify({
        'status': 'success',
        'message': 'The device information has been set.'
    })


@device_bp.route("/positions/statistics", methods=["GET"])
def query_devices_positions_statistics():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') or 50000
    offset = request.args.get('offset') or 0

    request.cursor.execute(query_all_location_info_sql_v2, (uid, limit, offset))

    location_items = request.cursor.fetchall()
    # total = query_user_device_size(request.cursor, redis_client, uid)
    request.cursor.execute(query_all_device_by_uid, (uid, limit, offset))
    all_device = request.cursor.fetchall()

    statistics = {
        "Asia": {"area": "Asia", "online": 0, "offline": 0},
        "Africa": {"area": "Africa", "online": 0, "offline": 0},
        "Europe": {"area": "Europe", "online": 0, "offline": 0},
        "South America": {"area": "South America", "online": 0, "offline": 0},
        "North America": {"area": "North America", "online": 0, "offline": 0},
        "Oceania": {"area": "Oceania", "online": 0, "offline": 0},
        "Antarctica": {"area": "Antarctica", "online": 0, "offline": 0},
        "Other": {"area": "Other", "online": 0, "offline": 0}
    }

    device_names = []
    for index, loc_item in enumerate(location_items):
        loc_item = LocationItem_v2._make(loc_item)
        device_names.append(loc_item.name)

        status = "offline"
        loc_item.online = False
        if redis_client.exists(loc_item.name):
            status = "online"
            loc_item.online = True

        continent = CONTINENTS.get(loc_item.continent_id, ("Other", "other"))[0]
        statistics[continent][status] += 1

    for oth in all_device:
        d = DeviceOnlineInfo._make(oth)
        if d.name not in device_names:
            status = "online" if redis_client.exists(d.name) else "offline"
            statistics["Other"][status] += 1

    show_statistics = [v for v in statistics.values() if v["online"] or v["offline"]]
    return jsonify(show_statistics)


@device_bp.route("/register", methods=["POST"])
def remote_register_device():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    name_list = get_json(request).get('names', [])
    model_id = get_json(request).get('model_id')
    customer_id = get_json(request).get('customer_id')
    user_id = get_json(request).get('user_id')

    owner = DccaUser.get_by_id(user_id)
    customer = DccaCustomer.get(customer_id)

    try:
        for name in name_list:
            device = Host(name, model_id, owner=owner, customer=customer)
            session.add(device)

        DccaUserLimit.make(owner)
        session.commit()
    except Exception:
        if IS_DEBUG:
            import traceback
            traceback.print_exc()
        raise DCCAException('Fail to create device')

    return jsonify({
        'status': 'success',
        'message': 'Success to create users'
    })


@device_bp.route("/softwares", methods=["GET"])
def get_softwares():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    device_name = request.args.get('device_id')
    solution = request.args.get('solution')
    version = request.args.get('version')

    query_solutions_command = query_solutions_by_device_sql \
        .format(device_name=device_name)

    if solution:
        auto_ota_flag = False
    else:
        auto_ota_flag = True

    extra_condition = ''
    if auto_ota_flag:
        request.cursor.execute(query_device_message, (device_name,))
        device_message = request.cursor.fetchone()
        if not device_message:
            return jsonify({
                "status": "fail",
                "message": "%s device not found." % device_name
            })
        device = Device_Msg._make(device_message)._asdict()
        if device['model_default_solution_id']:
            if device['device_owner_id'] == device['model_owner_id']:
                extra_condition = " AND S.id = {}".format(device['model_default_solution_id'])
            else:
                request.cursor.execute(count_solutions, (device['model_id'], device['device_owner_id']))
                if request.cursor.fetchone()[0]:
                    extra_condition = " AND S.owner_id = {}".format(device['device_owner_id'])
                else:
                    extra_condition = " AND S.id = {}".format(device['model_default_solution_id'])
        else:
            if device['model_permission']:
                request.cursor.execute(count_solutions, (device['model_id'], device['device_owner_id']))
                if request.cursor.fetchone()[0]:
                    extra_condition = " AND S.owner_id = {}".format(device['device_owner_id'])
                else:
                    extra_condition = " AND S.is_public IS TRUE"
            else:
                extra_condition = "AND S.owner_id = {}".format(device['model_owner_id'])
        if not version:
            version = "1806"
    else:
        if solution:
            extra_condition = " AND S.solution = '{}'".format(solution)

    if version:
        if extra_condition:
            extra_condition = extra_condition + " AND S.version = '{}'".format(version)
        else:
            extra_condition = " AND S.version = '{}'".format(version)

    query_solutions_command = query_solutions_command + extra_condition + " ORDER BY S.id ASC"
    request.cursor.execute(query_solutions_command)
    rows = request.cursor.fetchall()

    Record = namedtuple('Record', ['sol_id', 'device_id', 'model_id', 'model', 'type', 'platform', 'vendor', 'solution',
                                   'version', 'url', 'public_key', 'is_signed', 'have_installer'])
    results = {"softwares": []}
    for row in rows:
        record = Record(*row)
        results['softwares'].append(record._asdict())

    return jsonify(results)


# @device_bp.route("/tasks", methods=["POST"])
# # def update_firmware():
# #     uid, err = get_oemid(request=request)
# #     if err is not None:
# #         return jsonify(UNAUTH_RESULT)


@device_bp.route("/tasks", methods=["GET"])
def query_all_tags():
    request.cursor.execute(query_all_tags_sql)
    tags = request.cursor.fetchall()
    results = []

    for tag in tags:
        tag = Tag._make(tag)
        results.append(tag._asdict())

    return jsonify(results)


@device_bp.route("/tasks/status", methods=["GET"])
def query_ota_status():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    mid = request.args.get('mid')
    inst = EsTaskOtaInst.get(mid)
    return jsonify(OTA_STATUS_MAP[inst.status])


@device_bp.route("/tasks/status", methods=["POST"])
def upload_ota_status():
    check_json(request)
    inst_id = get_json(request).get('mid')
    status = get_json(request).get('status')
    device_name = get_json(request).get('device')
    solution_id = get_json(request).get('solutionid')

    device = Host.get_by_name(device_name)
    empty_check(device, error_message='Device not exist or cannot access')

    if not inst_id:
        try:
            device.solution_id = solution_id
            session.add(device)
            session.commit()
            return jsonify({
                'device': device_name,
                'message': 'Upload OTA status success.'
            })
        except Exception:
            raise DCCAException('Fail to update OTA status..')
    else:
        inst = EsTaskOtaInst.get(inst_id)
        try:
            status_code = OTA_STATUS_NAMES[status]
            if status_code in TASK_STARTED_OTA_STATUS:
                inst.status = status_code
                inst.task.status = TASK_STATUS_STARTED
            elif status_code in TASK_COMPLETE_OTA_STATUS:
                inst.status = status_code
                inst.task.status = TASK_STATUS_COMPLETE
            else:
                inst.status = OTA_TASK_CODE_UNKNOWN
                inst.task.status = TASK_STATUS_UNKNOWN

            if status == OTA_TASK_STATUS_COMPLETE:
                device.solution_id = solution_id
                session.add(device)

            session.add(inst)
            session.commit()

            return jsonify({
                'device': inst.device.name,
                'mid': inst_id,
                'message': 'Upload OTA status success.'
            })
        except Exception:
            if IS_DEBUG:
                import traceback
                traceback.print_exc()
            raise DCCAException('Fail to update OTA status')


@device_bp.route("/type", methods=["GET"])
def query_model_by_uid():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    uid = request.args.get('uid', '')
    if len(uid) < 32:
        return jsonify({
            'status': 'failed',
            'message': 'uid length must be greater than 32'
        })

    query_model_sql_command = query_device_model_by_uid_sql.format(uid=uid[:32])
    request.cursor.execute(query_model_sql_command)
    model = request.cursor.fetchone()
    if model is None:
        return jsonify({})

    model = Device_Model._make(model)._asdict()
    del model['device_id']
    return jsonify(model)


@device_bp.route("/unenrollment", methods=["POST"])
def unenroll_device():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    name = get_json(request).get('deviceid')
    empty_check(name, error_message='The "device_name" can not be empty.')

    device = Host.query_by_name(name)
    if not device:
        return jsonify({
            'status': 'fail',
            'message': 'Device not exist or cannot access'
        })

    payload = {
        'action': 'unenroll'
    }

    EsTaskOtaInst.publish(MQTT_HOST, payload, name=name)
    return jsonify({
        'status': 'success',
        'data': 'Start to unenroll device, this may take several minutes.'
    })


def query_user_device(cursor, device_id, uid):
    cursor.execute(query_one_device_sql, (device_id, uid, uid))
    size = cursor.fetchone()[0]
    return size


@device_bp.route("/<device_id>", methods=["DELETE"])
def delete_device_by_id_v2(device_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    count = query_user_device(request.cursor, device_id, uid)
    if count == 0:
        return jsonify({
            'status': 'fail',
            'message': 'Incorrect device ID or no permission to access'
        })

    # Remove the model-device mapping   TODO remove later
    try:
        request.cursor.execute(delete_ass_host_model_sql, (device_id,))
    except Exception:
        raise DCCAException('Error to remove model of device')

    # Remove the user-device mapping
    try:
        request.cursor.execute(delete_ass_user_host_sql, (device_id,))
    except Exception:
        raise DCCAException('Error to remove user of device')

    # Delete the tags of the device
    try:
        request.cursor.execute(delete_ass_device_tag_sql, (device_id,))
    except Exception:
        raise DCCAException('Error to remove tag of device')

    # Delete in dcca_progress
    try:
        request.cursor.execute(delete_progress_sql, (device_id,))
    except Exception:
        raise DCCAException('Error to remove device progress')

    # Delete the device tasks
    try:
        request.cursor.execute(delete_ass_device_task_sql, (device_id,))
    except Exception:
        raise DCCAException('Error to remove device tasks')

    # Delete the records in dcca_tasks
    try:
        request.cursor.execute(delete_solution_task_sql, (device_id,))
    except Exception:
        raise DCCAException('Error to remove solution tasks')

    # Delete the records in dcca_deploy_records
    try:
        request.cursor.execute(delete_deploy_record_sql, (device_id,))
    except Exception:
        raise DCCAException('Exception, fail to remove deploy records')

    # Remove OTA task instance
    try:
        request.cursor.execute(delete_ota_task_inst_sql, (device_id,))
    except Exception:
        raise DCCAException('Exception, fail to remove OTA records')

    # Remove device group device_id
    try:
        request.cursor.execute(delete_group_device_id_sql, (device_id,))
    except Exception:
        raise DCCAException('Exception, fail to delete device in group')

    # Remove related tasks and instances
    try:
        request.cursor.execute(query_task_by_inst_sql, (device_id,))
        tasks = request.cursor.fetchall()
        for task in tasks:
            task_id = task[0]
            request.cursor.execute(delete_task_inst_sql, (device_id,))
            request.cursor.execute(count_task_inst_sql, (task_id,))
            count = request.cursor.fetchone()[0]
            if count == 0:
                request.cursor.execute(delete_task_by_id_sql, (task_id,))
    except Exception:
        raise DCCAException('Exception, fail to delete task records.')

    # Remove the device
    try:
        request.cursor.execute(delete_device_sql, (device_id,))
        request.conn.commit()
    except Exception:
        raise DCCAException('Error to remove device')

    decr_device_counter(redis_client, user_id=uid)
    result = OrderedDict()
    result['status'] = 'success'
    result['message'] = 'Success to remove device'

    return jsonify(result)


@device_bp.route("/<device_id>", methods=["GET"])
def query_one_device_v2(device_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not device_id:
        return jsonify({
            'status': 'fail',
            'message': 'The "device_id" cannot be empty'
        })

    count = query_user_device(request.cursor, device_id, uid)
    if count == 0:
        return jsonify({
            'status': 'fail',
            'message': 'Incorrect device ID or no permission to access'
        })

    tags = query_device_tags(request.cursor, device_id)

    data = OrderedDict()
    data['device_info'] = OrderedDict()
    data['tags'] = tags

    device = query_device(request.cursor, device_id)
    device_name = device['name']

    # I really don't want to write like this
    device_uid, model, _type, platform, vendor = device_name.split('.')

    data['device_info']['id'] = device['id']
    data['device_info']['uid'] = device_uid
    data['device_info']['name'] = device_name
    data['device_info']['certname'] = device['certname']
    data['device_info']['created_at'] = device['created_at']
    data['device_info']['updated_at'] = device['updated_at']
    data['device_info']['display_name'] = device['display_name']
    data['device_info']['mode'] = OrderedDict()
    data['device_info']['mode']['model'] = model
    data['device_info']['mode']['type'] = _type
    data['device_info']['mode']['platform'] = platform
    data['device_info']['mode']['vendor'] = vendor
    data['device_info']['solution'] = OrderedDict()
    data['device_info']['solution']['name'] = device['solution']
    data['device_info']['solution']['version'] = device['version']

    device_status = query_one_device_status(device_name)
    data['device_info'].update(device_status)
    data['device_info']['created_at'] = data['device_info']['created_at'].strftime('%Y-%m-%d %H:%M:%S') \
        if data['device_info']['created_at'] else None
    data['device_info']['updated_at'] = data['device_info']['updated_at'].strftime('%Y-%m-%d %H:%M:%S') \
        if data['device_info']['updated_at'] else None

    return jsonify(data)


@device_bp.route("/<device_id>", methods=["PUT"])
def modify_one_device(device_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    display_name = get_json(request).get('display_name')

    try:
        update_device(request.cursor, device_id, display_name)
    except Exception:
        raise DCCAException('Exception, fail to update device')

    request.conn.commit()
    return jsonify({
        'status': 'success',
        'message': 'Success to update device.'
    })


@device_bp.route("/<device_id>/endpoints", methods=["GET"])
def device_get_endpoint(device_id):
    def_endpoints["api"]["uri"] = API_URI
    def_endpoints["mqtt"]["uri"] = MQTT_URI
    def_endpoints["docker_content_trust_server"] = docker_content_trust_server
    endpoints = copy.deepcopy(def_endpoints)

    request.cursor.execute(query_model_by_did, {"like": device_id + '%'})
    model = request.cursor.fetchone()
    if not model:
        return jsonify(endpoints)

    request.cursor.execute(query_oem_by_model, model[0].split('.')[1:])
    oem = request.cursor.fetchone()
    if not oem:
        return jsonify(endpoints)
    else:
        oem = OEM._make(oem)._asdict()

    if oem['chain']:
        endpoints['oem_trust_ca'] = oem['chain'].strip() \
            .encode('base64').strip().replace('\n', '')

    request.cursor.execute(query_services_by_uid, (oem['user_id'],))
    services = request.cursor.fetchall()
    for service in services:
        endpoint = EndPoint._make(service)._asdict()
        if not endpoint['name'].lower().find('dockernotary'):
            endpoints['docker_content_trust_server'] = endpoint['url'] if endpoint['port'] in ['443', ""] else endpoint['url'] + ":" + endpoint['port']
        elif not endpoint['name'].lower().find('restapi'):
            endpoints['api'] = dict({'uri': endpoint['url'] if endpoint['port'] in ['443', ""] else endpoint['url'] + ":" + endpoint['port']})
        elif not endpoint['name'].lower().find('message'):
            endpoints['mqtt'] = dict({'uri': endpoint['url'] + ":" + endpoint['port']})
        elif not endpoint['name'].lower().find('dockerrepo'):
            endpoints['docker_trust_token'] = endpoint['access_token']
        else:
            endpoints.update(
                dict({endpoint['name'].lower().replace(" ", "_"): endpoint['url'] + ":" + endpoint['port']}))
    return jsonify(endpoints)


def device_owner_blurred_filter():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    tag_ids = request.args.get('tag_ids')

    query_device_blurred_by_tag_sql = 'SELECT DISTINCT D.id, D.name' \
                                      ' FROM hosts AS D'
    where = ''
    for index, tag_id in enumerate(tag_ids):
        query_device_blurred_by_tag_sql += ' LEFT JOIN dcca_ass_device_tag AS T{}'.format(index)
        query_device_blurred_by_tag_sql += ' ON D.id=T{}.device_id'.format(index)
        where += ' AND T{}.tag_id={}'.format(index, tag_id)

    query_device_blurred_by_tag_sql += ' WHERE'
    query_device_blurred_by_tag_sql += ' D.owner_id={user_id}'
    query_device_blurred_by_tag_sql += where

    request.cursor.execute(query_device_blurred_by_tag_sql.format(user_id=uid))
    devices = request.cursor.fetchall()

    results = {'devices': []}
    for dev in devices:
        dev = Device._make(dev)
        d = OrderedDict()
        d['id'] = dev.id
        d['name'] = dev.name
        results['devices'].append(d)

    return jsonify(results)


@device_bp.route("/tags", methods=["GET"])
def query_all_tags_v2():
    request.cursor.execute(query_all_tags_sql)
    tags = request.cursor.fetchall()
    results = []

    for tag in tags:
        tag = Tag._make(tag)
        results.append(tag._asdict())

    return jsonify(results)


@device_bp.route("/tags", methods=["POST"])
def attach_tag_to_devices():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    tag_name = get_json(request).get('tag_name')
    device_ids = get_json(request).get('device_ids')

    device_ids_str = ','.join(map(str, device_ids))
    # Check if the user is the owner of given devices
    count_devices_command = count_not_owned_devices_sql.format(user_id=uid, device_ids=device_ids_str)
    request.cursor.execute(count_devices_command)
    count = request.cursor.fetchone()[0]
    if len(device_ids) != count:
        return jsonify({
            'error': True,
            'status': 'fail',
            'message': 'Unauthorized devices found'
        })

    if not tag_name:
        return jsonify({
            'status': 'fail',
            'message': 'Tag cannot be emtpy'
        })

    # Query tag
    tag_id = query_tag(request.cursor, tag_name)

    if not tag_id:
        tag_id = create_tag(request.cursor, tag_name)

    device_tag_ids = []
    for device_id in device_ids:
        device_tag_ids.append((device_id, tag_id,))

    attach_tag_to_devices_command = attach_tag_to_devices_sql.format(device_tag_ids_str=str(device_tag_ids).strip('[]'))
    try:
        request.cursor.execute(attach_tag_to_devices_command)
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to attach tag to devices due to DB error')

    return jsonify({
        'status': 'success',
        'message': 'Success to attach tag to devices'
    })


@device_bp.route("/<device_id>/tags", methods=["DELETE"])
def remove_tag_from_device(device_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    tag_name = get_json(request).get('name')
    if not tag_name:
        return jsonify({
            'status': 'fail',
            'message': 'Tag name cannot be empty'
        })

    # query device name by id
    device_owner = check_device_owner_by_id(request.cursor, device_id, uid)
    if not device_owner:
        return jsonify({
            'status': 'fail',
            'message': 'Device not exist or you have no permission'
        })

    # Query tag
    tag_id = query_tag(request.cursor, tag_name)
    if not tag_id:
        return jsonify({
            'status': 'success',
            'message': 'Device does not have the tag'
        })

    # Remove tag from device
    try:
        request.cursor.execute(remove_tag_from_device_sql, (device_id, tag_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to remove tag from device')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove tag from device'
    })
