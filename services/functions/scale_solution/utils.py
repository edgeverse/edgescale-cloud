# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from datetime import datetime

from botocore.exceptions import ClientError

from edgescale_pyutils.common_utils import get_current_utc_timestamp, get_utc_timestamp_from_time
from edgescale_pyutils.exception_utils import DCCAException
from model import redis_client
from model.raw_sqls import *


def query_tag(cursor, tag_name):
    """
    Query tag by name
    RET: tag id
    """
    query_tag_command = query_tag_sql.format(name=tag_name)
    cursor.execute(query_tag_command)
    tag = cursor.fetchone()
    if tag:
        return tag[0]
    else:
        return None


def query_exist_tag(cursor, tag_names):
    find_tag_id, not_find_tag_name = [], []
    if not tag_names:
        return find_tag_id, not_find_tag_name

    query_tags_command = query_tags_sql % ",".join(["'%s'" % i for i in tag_names])
    cursor.execute(query_tags_command)
    tags = cursor.fetchall()

    find_tag_dict = {i[1]: i[0] for i in tags}
    for tag_name in tag_names:
        if tag_name not in find_tag_dict:
            not_find_tag_name.append(tag_name)

    return find_tag_dict.values(), not_find_tag_name


def create_tags(cursor, tag_names):
    if not tag_names:
        return []
    try:
        create_tags_command = create_tags_sql.format(names=",".join(["('%s')" % i for i in tag_names]))
        cursor.execute(create_tags_command)
        result = cursor.fetchall()
        tag_ids = [i[0] for i in result]
        return tag_ids
    except Exception:
        raise DCCAException("create tag filed.")


def query_solution_has_tag_ids(cursor, solution_id, tag_ids):
    if not tag_ids:
        return []

    query_solution_tags_command = query_solution_tags_sql.format(sol_id=solution_id,
                                                                 tag_ids=",".join([str(i) for i in tag_ids]))

    cursor.execute(query_solution_tags_command)
    result = cursor.fetchall()
    tag_ids = [i[0] for i in result]

    return tag_ids


def bind_solution_with_tags(cursor, solution_id, tag_ids):
    if not tag_ids:
        return []

    values = ",".join(["(%s,%s)" % (solution_id, i) for i in tag_ids])
    create_solution_command = create_solution_tags_sql.format(values=values)

    try:
        cursor.execute(create_solution_command)
        result = cursor.fetchall()
        ids = [i[0] for i in result]
        return ids
    except Exception:
        raise DCCAException("bind tag to solution filed.")


try:
    from model import dynamodb, DEVICE_STATUS_TABLE

    def query_one_device_status(device_name):
        # table:edgescale_device_status
        try:
            table = dynamodb.Table(DEVICE_STATUS_TABLE)
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
