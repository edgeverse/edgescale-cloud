# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from datetime import datetime

from botocore.exceptions import ClientError

from edgescale_pyutils.common_utils import get_current_utc_timestamp, get_utc_timestamp_from_time, hashabledict
from edgescale_pyutils.exception_utils import DCCAException
from model import redis_client
from model.constants import *
from model.raw_sqls import *


BIND_MODEL_EX_SEC = 1800
CREATE_DEVICE_EX_SEC = 1800
CREATE_DEVICE_MAX_LIMIT_EX_SEC = 3600


def _ck_bind_model(user_id, model_id):
    return 'j2:%s:%s:ubm' % (user_id, model_id)


def _ck_create_device(user_id):
    # ck stands for cache key, cdc for "create device counter"
    return 'j2:%s:cdc' % user_id


def _ck_create_device_max_limit(user_id):
    return 'j2:%s:cdmax' % user_id


def query_device_tags(cursor, device_id):
    tags = []
    cursor.execute(query_device_tags_sql_v2, (tuple([device_id]), ))
    device_tag_items = cursor.fetchall()
    for dt in device_tag_items:
        dt = DeviceTag._make(dt)
        tags.append({
            'id': dt.tag_id,
            'name': dt.tag_name
        })

    return tags


def query_device(cursor, device_id):
    cursor.execute(query_device_v2_sql, (device_id, ))
    device = cursor.fetchone()
    if device:
        device = DeviceInfo._make(device)
        return device._asdict()
    else:
        return None


def query_max_limit(cursor, user_id, limit_type_id=LIMIT_TYPE_CAN_BIND):
    cursor.execute(query_device_limit_sql, (user_id, limit_type_id))
    max_limit = cursor.fetchone()
    if max_limit:
        return max_limit[0]
    else:
        return NO_MAX_LIMIT


def exceed_max_model_number(cursor, redis_client, user_id, model_id):
    binding_number = count_user_bind_model(cursor, redis_client, user_id, model_id)
    can_bind_number = query_max_limit(cursor, user_id)
    if binding_number >= can_bind_number:
        return True
    else:
        return False


def exceed_max_device_number(cursor, redis_client, user_id):
    max_limit = redis_client.get(_ck_create_device_max_limit(user_id))
    if max_limit is None:
        max_limit = query_max_limit(cursor, user_id=user_id, limit_type_id=LIMIT_TYPE_DEVICE)
        redis_client.set(_ck_create_device_max_limit(user_id), max_limit, ex=CREATE_DEVICE_MAX_LIMIT_EX_SEC)

    current_device_size = get_device_counter(redis_client, user_id)
    if current_device_size is None:
        # owner_id=user_id OR oem_uid=user_id
        cursor.execute(count_current_devices_sql, (user_id, user_id))
        current_device_size = cursor.fetchone()[0]
        set_device_counter(redis_client, user_id, current_device_size)

    if current_device_size >= int(max_limit):
        return True, max_limit
    else:
        return False, max_limit


def count_user_bind_model(cursor, redis_client, user_id, model_id):
    size = get_user_bind_model_counter(redis_client, user_id, model_id)
    if size is None:
        cursor.execute(query_user_bind_model_sql, (model_id, user_id))
        size = cursor.fetchone()[0]
        set_user_bind_model_counter(redis_client, user_id, model_id, size)
    return size


def get_user_bind_model_counter(redis_client, user_id, model_id):
    ubm_key = _ck_bind_model(user_id, model_id)
    size = redis_client.get(ubm_key)
    if size:
        return int(size)
    else:
        return size


def set_user_bind_model_counter(redis_client, user_id, model_id, size):
    ubm_key = _ck_bind_model(user_id, model_id)
    return redis_client.set(ubm_key, size, ex=BIND_MODEL_EX_SEC)


def incr_user_bind_model_counter(redis_client, user_id, model_id):
    ubm_key = _ck_bind_model(user_id, model_id)
    return redis_client.incr(ubm_key)


def get_device_counter(redis_client, user_id):
    cd_key = _ck_create_device(user_id)
    size = redis_client.get(cd_key)
    if size is not None:
        return int(size)
    else:
        return None


def set_device_counter(redis_client, user_id, size):
    cd_key = _ck_create_device(user_id)
    return redis_client.set(cd_key, size, ex=CREATE_DEVICE_EX_SEC)


def incr_create_device_counter(redis_client, user_id):
    cd_key = _ck_create_device(user_id)
    redis_client.incr(cd_key)


def decr_device_counter(redis_client, user_id):
    cd_key = _ck_create_device(user_id)
    size = redis_client.get(cd_key)
    if size is not None:
        redis_client.decr(cd_key)


def is_device_owner(cursor, user_id, device_ids):
    cursor.execute(check_device_owner_v2_sql, (user_id, tuple(device_ids)))
    size = cursor.fetchone()[0]
    if size >= len(device_ids):
        return True
    else:
        return False


def query_device_location(cursor, user_id, device_ids, limit=2000, offset=0):
    cursor.execute(query_device_location_info_v2_sql, (user_id, tuple(device_ids), limit, offset))
    locations = cursor.fetchall()
    return locations


def make_record_deploy_times(client, rest_api_id, user_id, redis_key, datetime_format='%Y%m%d'):
    # Save deploy as {rest_api_id}:{user_id}:{datetime}:{key-word} in redis
    utc_time_now = datetime.utcnow()
    datetime_key = utc_time_now.strftime(datetime_format)
    redis_key = redis_key.format(rest_api_id=rest_api_id, user_id=user_id, datetime=datetime_key)
    client.hincrby(redis_key, utc_time_now.hour, 1)


def update_device(cursor, device_id, display_name):
    cursor.execute(update_device_sql, (display_name, device_id))


def is_oem_user(cursor, uid):
    try:
        cursor.execute('select account_type_id from dcca_users where id=%s;', (uid, ))
        u = cursor.fetchone()[0]
        if int(u) == 2:
            return True
    except Exception:
        return False
    return False


def get_oem_uid_by_device_name(cursor, device_name):
    try:
        cursor.execute(query_oem_users_by_device_name_sql, (device_name,))
        r = cursor.fetchone()
        if r:
            return r[0], r[1]
    except Exception:
        return 0, None
    return 0, None


def bind_device_owner(cursor, device_name, uid):
    oemuid, device_name = get_oem_uid_by_device_name(cursor, device_name)

    # update owner_id if owner_id equcals oem_uid
    try:
        cursor.execute(bind_device_owner_sql, (uid, device_name, oemuid))
        device_id = cursor.fetchone()[0]
        if device_id:
            cursor.execute(create_device_owner_sql, (uid, device_id,))
            return device_id
    except Exception:
        return None
    return None


def query_tag(cursor, tag_name):
    """
    Query tag by name
    RET: tag id
    """
    cursor.execute(query_tag_sql, (tag_name, ))
    tag = cursor.fetchone()
    if tag:
        return tag[0]
    else:
        return None


def create_tag(cursor, tag_name):
    create_tag_command = create_tag_sql.format(name=tag_name)
    cursor.execute(create_tag_command)
    tag_id = cursor.fetchone()[0]

    return tag_id


def check_device_owner_by_id(cursor, device_id, user_id):
    cursor.execute(check_device_owner_sql, (device_id, user_id))

    count = cursor.fetchone()[0]

    if count == 0:
        return False
    else:
        return True


def device_solution_filter(cursor, uid, limit, offset, solution_id):
    query_device_command = query_device_by_solution_sql.format(uid=uid, limit=limit,
                                                               offset=offset,
                                                               solution_id=solution_id)
    cursor.execute(query_device_command)
    devices = cursor.fetchall()
    results = []

    for device in devices:
        devce_data = hashabledict({
            'id': device[0],
            'name': device[1]
        })
        results.append(devce_data)

    return set(results)


try:
    from model import dynamo, device_status_table

    def query_one_device_status(device_name):
        # table:edgescale_device_status
        try:
            table = dynamo.Table(device_status_table)
            response = table.get_item(
                Key={
                    'deviceId': device_name
                }
            )

            result = {
                "status": "offline",
                "last_report": None,
                "cpu_usage": None,
                "cpu_num": None,
                "cpu_freq": None,
                "mem_usage": None,
                "mem_total": None,
                "app_num": None,
                "app_list": None,
                "es_version": None,
                "local_ip": None,
                "disk_free": None,
                "disk_used": None,
            }

            if 'Item' in response:
                report_time = response['Item']['last_report']

                current_timestamp = get_current_utc_timestamp()
                report_timestamp = get_utc_timestamp_from_time(
                    datetime.strptime(str(report_time), '%Y-%m-%dT%H:%M:%SZ'))
                interval = current_timestamp - report_timestamp
                if interval > 180:
                    result['status'] = "offline"
                else:
                    def _response_filter(response):
                        def func(name):
                            if name in response['Item']:
                                return response['Item'][name]
                            else:
                                return None

                        return func

                    _filter = _response_filter(response)

                    result['status'] = "online"
                    result['cpu_usage'] = _filter('cpu_usage')
                    result['cpu_num'] = _filter('cpu_num')
                    result['cpu_freq'] = '{:0.1f}GHz'.format(_filter('cpu_freq') / 1000000) \
                        if _filter('cpu_freq') \
                        else None

                    result['mem_usage'] = _filter('mem_usage')
                    result['mem_total'] = '{:0.1f}GB'.format(_filter('mem_total') / 1000000) \
                        if _filter('mem_total') \
                        else None

                    result['app_num'] = _filter('app_num')
                    result['app_list'] = ','.join(_filter('app_list')) \
                        if result['app_num'] and int(result['app_num']) > 0 \
                           and _filter('app_list') \
                        else None

                    result['es_version'] = _filter('es_version')
                    result['local_ip'] = _filter('ip_address')
                    result['disk_free'] = _filter('disk_free')
                    result['disk_used'] = _filter('disk_used')

                result['last_report'] = report_time.replace("T", " ").strip("Z")

            return result
        except ClientError as e:
            print((e.response['Error']['Message']))
            raise DCCAException('Fail to query device status')
except Exception:
    def query_one_device_status(device_name):
        # hash:device_name
        value = redis_client.hgetall(device_name)
        if value:
            report_time = value.get("Timestamp", "")
            ds = {
                "cpu_freq": "{:0.1f}GHz".format(int(value["CPUFreq"]) / 1000000) if "CPUFreq" in value else None,
                "mem_total": "{:0.1f}GB".format(int(value["MemTotal"]) / 1000000) if "MemTotal" in value else None,
                "app_list": value['AppList'] if int(value.get("AppNumber", 0)) > 0 and "AppList" in value else None,
                "last_report": report_time.replace("T", " ").strip("Z"),
                "local_ip": value.get("IpAddr"),
                "status": "online",
                "cpu_usage": value.get("CPUUsage"),
                "cpu_num": value.get("CPUNum"),
                "mem_usage": value.get("MemUsage"),
                "app_num": value.get("AppNumber"),
                "es_version": value.get("EsVersion"),
                "disk_free": value.get("DiskFree"),
                "disk_used": value.get("DiskUsed")
            }
            current_timestamp = get_current_utc_timestamp()
            report_timestamp = get_utc_timestamp_from_time(datetime.strptime(str(report_time), '%Y-%m-%dT%H:%M:%SZ'))
            interval = current_timestamp - report_timestamp
            if interval > 180:
                ds['status'] = "offline"
        else:
            ds = {
                "status": "offline",
                "last_report": None,
                "cpu_usage": None,
                "cpu_num": None,
                "cpu_freq": None,
                "mem_usage": None,
                "mem_total": None,
                "app_num": None,
                "app_list": [],
                "es_version": None,
                "local_ip": None,
                "disk_free": None,
                "disk_used": None,
            }
        return ds
