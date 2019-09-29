# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import json
import pickle
import random
import time
import unicodedata
from collections import OrderedDict
from datetime import datetime, timedelta

import boto3
import botocore
import requests

from edgescale_pyutils.exception_utils import InvalidParameterException
from model import HARBORPASSWD, redis_client
from model.constants import DATE_TIME_FORMAT, DATE_TIME_DAY_FORMAT, CACHE_KEY_API_USAGE, DATE_FORMAT_LONG, \
    DATE_FORMAT_SHORT, CACHE_KEY_CREATE_DEVICE, LIMIT_TYPE_MODEL, SimpleService, Service, HARBOR_API, certs, \
    ShortDevice, LIMIT_TYPE_DEPLOY_ID, REDIS_KEY_DEPLOY_FORMAT, DATETIME_FORMAT
from model.raw_sqls import *


def validate_time_format(date_text):
    try:
        datetime.strptime(date_text, DATE_TIME_FORMAT)
    except ValueError:
        raise ValueError('Incorrect data format, should be YYYY-MM-DD HH')


def validate_datetime_format(date_text):
    try:
        datetime.strptime(date_text, DATE_TIME_DAY_FORMAT)
    except ValueError:
        raise ValueError('Incorrect data format, should be {}'.format(DATE_TIME_DAY_FORMAT))


def validate_host_network(host_network):
    if host_network is None or host_network == '':
        pass
    elif not isinstance(host_network, bool):
        raise InvalidParameterException('The host network should be a boolean type')


def validate_cap_add(cap_add):
    if cap_add is None or cap_add == '':
        pass
    elif not isinstance(cap_add, bool):
        raise InvalidParameterException('The "cap_add" should be a boolean type.')


def validate_ports(ports):
    if not isinstance(ports, list):
        raise InvalidParameterException('Invalid port type')
    elif not ports:
        return None
    elif len(ports) == 1 \
        and 'hostPort' in ports[0] and 'containerPort' in ports[0] \
        and ports[0]['hostPort'] == '' and ports[0]['containerPort'] == '':
        return None
    elif len(ports) == 1 \
        and 'hostPort' in ports[0] and 'containerPort' in ports[0] \
        and (ports[0]['hostPort'] == '' or ports[0]['containerPort'] == ''):
        raise InvalidParameterException('Invalid port')
    elif len(ports):
        for port in ports:
            if 'hostPort' not in port or 'containerPort' not in port:
                raise InvalidParameterException('Invalid port format, lack of "hostPort" or "containerPort".')
            elif port['hostPort'] == '' or port['containerPort'] == '':
                raise InvalidParameterException('Invalid port format, cannot be empty')
        return ports

    raise InvalidParameterException('Invalid ports type')


def validate_volumes_v2(volumes):
    """
    "dynamic_volumes": [{"hostPath": {"path": ""}, "name": ""}],
    "dynamic_volumeMounts": [{"readOnly": true, "mountPath": "", "name": ""}]
    """
    if not isinstance(volumes, list):
        raise InvalidParameterException('Invalid volumes type, not list.')
    elif not volumes:
        return None, None
    elif len(volumes) == 1 \
            and volumes[0]['hostPath'].strip() == '' \
            and volumes[0]['mountPath'].strip() == '':
        return None, None

    # dynamic_volumes, dynamic_volumeMounts
    dynamic_volumes = []
    dynamic_volume_mounts = []
    for _index, volume in enumerate(volumes):
        if 'hostPath' not in volume or 'mountPath' not in volume:
            raise InvalidParameterException('Invalid parameter, hostPath or mountPath required.')
        if volume['hostPath'] == '' or volume['mountPath'] == '':
            raise InvalidParameterException('Invalid parameter, hostPath or mountPath can not be empty.')

        host_path = volume['hostPath']
        mount_path = volume['mountPath']

        if 'mountPathReadOnly' in volume:
            read_only = True if volume['mountPathReadOnly'] else False
        else:
            read_only = False

        volume_name = 'volume' + str(_index)
        dynamic_volumes.append({
            "hostPath": {"path": host_path},
            "name": volume_name
        })

        dynamic_volume_mounts.append({
            "readOnly": read_only,
            "mountPath": mount_path,
            "name": volume_name
        })

    return dynamic_volumes, dynamic_volume_mounts


def validate_time(start_utc_time, end_utc_time, time_format=DATE_TIME_FORMAT, validate_func=validate_time_format):
    if not start_utc_time or not end_utc_time:
        return {
            'status': 'fail',
            'message': 'The start time or end time cannot be empty'
        }

    try:
        validate_func(start_utc_time)
    except ValueError as e:
        return {
            'status': 'fail',
            'message': str(e)
        }

    try:
        validate_func(end_utc_time)
    except ValueError as e:
        return {
            'status': 'fail',
            'message': str(e)
        }

    start_utc_date = datetime.strptime(start_utc_time, time_format)
    end_utc_date = datetime.strptime(end_utc_time, time_format)

    delta = end_utc_date - start_utc_date
    if delta.days == -1:
        return {
            'status': 'fail',
            'message': 'Invalid time, start time should before end time.'
        }

    return {
        'status': 'success',
        'message': 'Valid time format'
    }


def date_long_to_short(date_str):
    return datetime.strptime(date_str, DATE_FORMAT_LONG).strftime(DATE_FORMAT_SHORT)


def calculate_access_dates(start_time, end_time, time_format=DATE_TIME_FORMAT):
    _start_time = datetime.strptime(start_time, time_format)
    _end_time = datetime.strptime(end_time, time_format)

    # Calculate time delta
    delta = _end_time - _start_time
    days = delta.days

    access_dates = []
    if days == 0:
        # Less than 24 hours
        if _start_time.date() == _end_time.date():
            access_dates.append(_start_time.date())
        else:
            access_dates.append(_start_time.date())
            access_dates.append(_end_time.date())
    else:
        access_dates.append(_start_time.date())

        start_date = _start_time.date()
        for i in range(1, days + 1):
            next_date = start_date + timedelta(days=1)
            access_dates.append(next_date)
            start_date = next_date
    return access_dates


def query_cached_access_records(user_id, date_str_list, cache_key=CACHE_KEY_API_USAGE):
    access_records = OrderedDict()
    not_cached_dates = []
    rest_api_id = redis_client.rest_api_id

    for date_str in date_str_list:
        date_key = date_long_to_short(date_str)
        query_key = cache_key.format(rest_api_id=rest_api_id, user_id=user_id, date_id=date_key)
        record = redis_client.hgetall(query_key)
        if record:
            access_records[date_key] = record
        else:
            not_cached_dates.append(date_str)

    return access_records, not_cached_dates


def query_db_access_records(cursor, user_id, date_str_list):
    access_records = OrderedDict()
    for index, date_str in enumerate(date_str_list):
        query_record_sql = 'SELECT record FROM dcca_api_access_records WHERE user_id=%s'
        query_record_sql += " AND access_date='{}' ;".format(date_str)

        cursor.execute(query_record_sql, (user_id, ))
        record = cursor.fetchone()
        if record:
            access_records[date_long_to_short(date_str)] = record[0]

    return access_records


def calculate_delta(cursor, user_id, start_time, end_time, time_format=DATE_TIME_FORMAT, cache_key=CACHE_KEY_API_USAGE):
    access_dates = calculate_access_dates(start_time, end_time, time_format)

    # Query all cached data that in redis
    cached_records, not_cached_dates = query_cached_access_records(user_id, list(map(str, access_dates)), cache_key)

    # Query no cached data
    not_cached_records = query_db_access_records(cursor, user_id, not_cached_dates)

    return OrderedDict(list(cached_records.items()) + list(not_cached_records.items()))


# TODO query data from not cached database
def query_api_usage(user_id, start_time, end_time, time_format, cache_key=CACHE_KEY_CREATE_DEVICE):
    access_dates = calculate_access_dates(start_time, end_time, time_format)
    cached_records, not_cached_dates = query_cached_access_records(user_id, list(map(str, access_dates)), cache_key)

    return OrderedDict(list(cached_records.items()))


def clock_time_filter(records):
    """
    Fill zero if no data
    """
    for date, usage in list(records.items()):
        not_access_hours = dict((str(k), 0) for k in range(24))
        for resource in list(usage.keys()):
            if not resource.isdigit():
                usage.pop(resource)
            elif resource in not_access_hours:
                del not_access_hours[resource]

        usage = dict(list(usage.items()) + list(not_access_hours.items()))
        records[date] = usage

    return records


def check_is_oxm(cursor, user_id):
    cursor.execute(query_user_account_type_sql, (user_id, ))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def check_model_exist(cursor, model, type, platform, vendor):
    cursor.execute(query_model_sql, (model, type, platform, vendor))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def device_type_max_limit(cursor, user_id):
    cursor.execute(query_max_limit_sql, (user_id, LIMIT_TYPE_MODEL))
    limit_size = cursor.fetchone()[0]
    return limit_size


def user_device_type_size(cursor, user_id):
    cursor.execute(count_all_models_sql, (user_id, ))
    size = cursor.fetchone()[0]
    return size


def exceed_model_max_limit(cursor, user_id):
    limit_size = device_type_max_limit(cursor, user_id)
    device_type_size = user_device_type_size(cursor, user_id)
    if device_type_size >= limit_size:
        return True
    else:
        return False


def check_model_owner(cursor, model_id, user_id):
    cursor.execute(count_model_owner_sql, (model_id, user_id))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def _check_binding(cursor, raw_sql_str, model_id):
    cursor.execute(raw_sql_str, (model_id, ))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def binding_to_ass_host_model(cursor, model_id):
    return _check_binding(cursor, binding_to_ass_host_model_sql, model_id)


def binding_to_solutions(cursor, model_id):
    return _check_binding(cursor, binding_to_solutions_sql, model_id)


def binding_to_devices(cursor, model_id):
    return _check_binding(cursor, binding_to_devices_sql, model_id)


def bind_to_device_ids(cursor, model_id):
    cursor.execute(bind_model_owner_sql, (model_id, ))
    device_ids = cursor.fetchall()
    return device_ids


def query_device_name(cursor, device_id, user_id):
    cursor.execute(query_devive_name_sql, (device_id, user_id))
    device_name = cursor.fetchone()[0]
    return device_name


def query_solution_name(cursor, model_id, user_id):
    cursor.execute(query_solution_name_sql, (model_id, user_id))
    device_name = cursor.fetchall()
    return device_name


def is_model_owner(cursor, model_id, user_id):
    cursor.execute(count_model_exist_sql, (model_id, user_id))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def make_service(service):
    service = Service._make(service)

    real_service = OrderedDict()
    real_service['id'] = service.uuid
    real_service['name'] = service.name
    real_service['cloudConfig'] = OrderedDict()
    real_service['cloudConfig']['protocol'] = service.protocal
    real_service['cloudConfig']['cipherSuite'] = service.cipher_suite
    real_service['cloudConfig']['serverCertificate'] = {
        'format': service.server_certificate_format,
        'key': service.server_certificate_key
    }
    real_service['cloudConfig']['connectionUrl'] = {'url': service.connection_url}
    real_service['cloudConfig']['config'] = service.config
    real_service['signingCertificate'] = OrderedDict()
    real_service['signingCertificate']['format'] = service.signing_certificate_format
    real_service['signingCertificate']['key'] = service.signing_certificate_key

    return real_service


def query_service(cursor, uid, suuid):
    """

    :param cursor: The DB cursor
    :param uid: User id
    :param suuid: Service uuid
    :return:
    """
    cursor.execute(query_service_by_id_sql, (uid, suuid))
    _service = cursor.fetchone()
    if not _service:
        return None
    else:
        return make_service(_service)


def query_user_name(cursor, uid):
    cursor.execute(query_name_sql, (uid,))

    r = cursor.fetchone()
    if r is None:
        raise Exception("no thus user")
    return r[0], r[1]


def query_harbor_userinfo(username):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    URL = "%s/users?username=%s" %(HARBOR_API, username)
    resp = requests.get(URL, headers=headers, auth=('admin', HARBORPASSWD), verify=False, timeout=10)

    if resp.status_code == 200:
        # update the user's passwd
        if len(resp.json()) > 0:
            return True, resp.json()[0]
    return False, {}


def update_user_passwd(userid):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    URL = "%s/users/%d/password" % (HARBOR_API, userid)

    passwd = "%x" % random.getrandbits(64)
    data = {
        "new_password": passwd
    }
    resp = requests.put(URL, headers=headers, auth=('admin', HARBORPASSWD), data=json.dumps(data), verify=False, timeout=10)

    if resp.status_code == 200:
        return True, passwd
    return False, "%d: %s" % (resp.status_code, resp.content)


def query_harbor_project(projectname):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    URL = "%s/projects?name=%s" %(HARBOR_API, projectname)
    resp = requests.get(URL, headers=headers, auth=('admin', HARBORPASSWD), verify=False, timeout=10)

    if resp.status_code == 200:
        if len(resp.json()) > 0:
            return True, resp.json()[0]
    return False, resp.status_code


def create_project(name):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    URL = "%s/projects" %(HARBOR_API)

    data = {
        "project_name": name,
        "metadata":  {"public": "true"}
    }
    resp = requests.post(URL, headers=headers, auth=('admin', HARBORPASSWD), data=json.dumps(data), verify=False, timeout=10)
    # 409 Conflict, means existed
    if resp.status_code in [201, 409]:
        time.sleep(0.1)
        return query_harbor_project(name)

    return False, resp.status_code


def add_member_to_project(username, projectid):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    URL = "%s/projects/%d/members" % (HARBOR_API, projectid)

    data = {
        "role_id": 1,
        "member_user": {"username": username}
    }
    resp = requests.post(URL, headers=headers, auth=('admin', HARBORPASSWD), data=json.dumps(data), verify=False, timeout=10)
    # 409 Conflict
    if resp.status_code in [201, 409]:
        return True, resp.status_code

    return False, resp.content


def create_user(name, passwd, email):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    URL = "%s/users" % (HARBOR_API, )

    data = {
        "username": name,
        "email":    email,
        "realname": name,
        "password": passwd,
        "comment":  "auto-registered"
    }
    resp = requests.post(URL, headers=headers, auth=('admin', HARBORPASSWD), data=json.dumps(data), verify=False, timeout=10)

    if resp.status_code == 201:
        time.sleep(0.1)
        return query_harbor_userinfo(name)

    return False, "%d: %s" % (resp.status_code, resp.content)


def get_docker_login_cmd(username, email):

    cmd = 'docker login -u {username} -p {passwd} registry.edgescale.org/{projectname}'

    if '@' not in email:
        email = "%s%d@edge.com" %(username.replace('@', ''), random.randint(1, 10))

    projectname = username.replace('@', '.')

    exist, u = query_harbor_userinfo(username)
    # print("query_harbor_userinfo", exist, u)
    # update the user's passwd
    if exist:
        s, passwd = update_user_passwd(u['user_id'])
        if s:
            success, p = create_project(projectname)
            add_member_to_project(u['username'], p['project_id'])
            return {
                "cmd": cmd.format(username=username, passwd=passwd, projectname=projectname),
                "status": "success"
            }

        return {
            'error': True,
            "message": "update_user_token: " + passwd,
            "status": "fail"
        }

    # user doesn't exist, create it
    else:
        passwd = "%x" % random.getrandbits(64)

        s, u = create_user(username, passwd, email)
        if s:
            s1, p = create_project(username)
            s2, r = add_member_to_project(u['username'], p['project_id'])
        else:
            return {
                'error': True,
                "message": "user sync error: %s %s" %(username, u),
                "status": "fail"
            }
        if s1 and s2:
            return {
                "cmd": cmd.format(username=username, passwd=passwd, projectname=projectname),
                "status": "success"
            }
        else:
            return {
                'error': True,
                "message": "user project sync error: %s %s" % (username, p),
                "status": "fail"
            }


def create_param_validate(cursor, **args):
    for k, v in list(args.items()):
        if k == 'name' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "name" cannot be empty.'
            }
        elif k == 'protocal' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "protocal" cannot be empty.'
            }
        elif k == 'cipher_suite' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "cipher_suite" cannot be empty.'
            }
        elif k == 'server_certificate_key' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "server_certificate_key" cannot be empty.'
            }
        elif k == 'server_certificate_format' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "server_certificate_format" cannot be empty.'
            }
        elif k == 'connection_url' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "connection_url" cannot be empty.'
            }
        elif k == 'config' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "config" cannot be empty.'
            }
        elif k == 'signing_certificate_format' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "signing_certificate_format" cannot be empty.'
            }
        elif k == 'signing_certificate_key' and not v:
            return {
                'status': 'Invalid',
                'message': 'The "signing_certificate_key" cannot be empty.'
            }
        elif k == 'model_id':
            model_id = v
            if not model_id:
                return {
                    'status': 'Invalid',
                    'message': 'The "model_id" cannot be empty.'
                }

            if not is_model_owner(cursor, v, model_id):
                return {
                    'status': 'Invalid',
                    'message': 'The model not accessable or not the model owner.'
                }

    return {
        'status': 'success',
    }


def make_error_msg(debug, error_msg, exception):
    if debug:
        error_msg += ' {}'.format(exception)
    return error_msg


def update_param_validate(cursor, **args):
    for k, v in list(args.items()):
        if k == 'server_certificate_format' and v:
            cursor.execute(query_server_cert_format_sql)
            formats = cursor.fetchone()[0]
            if v not in formats.strip('{}').split(','):
                return {
                    'status': 'Invalid',
                    'message': 'Invalid server certificate format'
                }
        elif k == 'signing_certificate_format' and v:
            cursor.execute(query_signing_cert_format_sql)
            formats = cursor.fetchone()[0]
            if v not in formats.strip('{}').split(','):
                return {
                    'status': 'Invalid',
                    'message': 'Invalid signing certificate format'
                }

    return {
        'status': 'success',
        'message': 'Valid parameters'
    }


def is_service_owner(cursor, user_id, service_id):
    cursor.execute(count_user_service_sql, (user_id, service_id))
    size = cursor.fetchone()[0]
    if size:
        return True
    else:
        return False


def update_service(cursor, name, url, port, access_token, service_id):
    cursor.execute(update_service_sql, (name, url, port, access_token, service_id))


def remove_one_service(cursor, service_id):
    cursor.execute(remove_one_service_sql, (service_id, ))


def get_bucket_region(bucket):
    s3 = boto3.client("s3")

    region = s3.get_bucket_location(Bucket=bucket)['LocationConstraint']
    return region


def get_presigned_url(bucket, key):
    acl = {"acl": "public-read"}

    region = get_bucket_region(bucket)
    s3 = boto3.client(
        's3',
        region_name=region,
        config=botocore.client.Config(signature_version='s3v4'))
    res = s3.generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Conditions=[acl]
    )
    res.update(acl)
    return res


def k8s_filter(content):
    if isinstance(content, (str, bytes)):
        ps = json.loads(content)
    else:
        ps = content
    return ps
    # # Return if http code is not 0
    # if ps.has_key('code') and ps['code'] != 0:
    #     # print "skip to parse the error message"
    #     # Handle error situation
    #
    #     d = OrderedDict()
    #     d['Code'] = ps.get('code')
    #     d['apiVersion'] = 'v1'
    #     d['error'] = ps.get('error')
    #     d['message'] = ps.get('message')
    #     return d
    #
    # d = OrderedDict()
    # #Why use Capital C ???
    # d['Code'] = 0
    # d['apiVersion'] = 'v1'
    # d['items'] = ps.get('items')
    # return d


def query_all_pods(query_status_resource, params=None):
    headers = {
        'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
        'Accept': 'application/json'
    }
    resp = requests.get(query_status_resource, params=params, cert=certs,
                        headers=headers, verify=False, timeout=7)
    return k8s_filter(resp.content)


def query_k8s_pods(cursor, query_status_resource, uid, params=None):
    k8s_pods = query_all_pods(query_status_resource, params=params)
    # origin_k8s_pods = {
    #     'code': 0,
    #     'apiVersion': 'v1',
    #     'limit': k8s_pods.get("limit", 0),
    #     'offset': k8s_pods.get("offset", 0),
    #     'total': k8s_pods.get("total", 0),
    #     'items': []
    # }

    nodes = {}
    node_index_dict = {}
    for _index, pod in enumerate(k8s_pods['items']):
        node_name = pod['metadata']['nodename']
        nodes[_index] = node_name
        if node_name not in node_index_dict:
            node_index_dict[node_name] = [_index]
        else:
            node_index_dict[node_name].append(_index)

    if not nodes:
        devices = []
    else:
        devices_sql_str = ' OR '.join(["D.name='{}'".format(n) for n in list(set(nodes.values()))])
        cursor.execute(query_owner_devices_sql.format(_sql_str=devices_sql_str), (uid,))
        devices = cursor.fetchall()

    for d in devices:
        device = ShortDevice._make(d)
        for index in node_index_dict[device.name]:
            data = k8s_pods['items'][index]
            data['metadata']['display_name'] = device.display_name

    return k8s_pods


def check_devices_owner(cursor, user_id, device_id):
    """
    :param cursor:
    :param user_id:
    :param device_id: is a list
    :return:
    """
    cursor.execute(check_device_owner_sql, (user_id, device_id))
    count = cursor.fetchone()[0]
    if count == 1:
        return True
    else:
        return False


def check_exceed_max_limit(cursor, uid, resource):
    cursor.execute(query_deploy_limits_sql, (uid, LIMIT_TYPE_DEPLOY_ID))
    max_size = cursor.fetchone()
    if max_size:
        user_k8s_pods = query_k8s_pods(cursor, resource, uid)
        if user_k8s_pods.get('total') >= max_size[0]:
            exceed = True
        else:
            exceed = False
    else:
        exceed = True

    return {
        'exceed_max': exceed
    }


def _limit_deploy_usage(client, user_id, res_key, max_limit=200, per_sec=3600):
    key = res_key.format(user_id)
    size = client.get(key)
    if size is None:
        size = 1
        client.setex(key, per_sec, size)
    elif int(size) >= max_limit:
        print('Exceed max limit')
        return {
            'status': 'fail',
            'message': 'You are too fast, try again later.'
        }
    else:
        client.incr(key)
        size = int(size)
        size += 1

    return {
        'status': 'success',
        'size': size
    }


def check_exceed_per_time_max_limit(cursor, client, user_id, limit_type_id, res_key):
    cursor.execute(query_per_time_limit_sql, (user_id, limit_type_id))
    limits = cursor.fetchall()
    max_limit, per_time = limits[0]

    result = _limit_deploy_usage(client, user_id, max_limit=max_limit, per_sec=per_time, res_key=res_key)

    return result


def jsonfy_commands(commands):
    if not commands:
        # commands is empty
        commands = ''
    elif isinstance(commands, list):
        commands = json.dumps(commands)
    elif isinstance(commands, str):
        commands = commands.strip()
        try:
            c = json.loads(commands)
            if isinstance(c, list):
                commands = json.dumps([unicodedata.normalize('NFKD', s).encode('utf8', 'ignore') for s in c])
        except ValueError:
            commands = json.dumps(commands.split(' '))

    return commands


def jsonfy_args(args):
    if not args:
        args = ''
    elif isinstance(args, list):
        args = json.dumps(args)
    elif isinstance(args, str):
        args = args.strip()
        args = json.dumps([args])

    return args


def make_record_deploy_times(client, rest_api_id, user_id, redis_key=REDIS_KEY_DEPLOY_FORMAT):
    # Save deploy as {rest_api_id}:{user_id}:{datetime} in redis
    utc_time_now = datetime.utcnow()
    datetime_key = utc_time_now.strftime(DATETIME_FORMAT)
    redis_key = redis_key.format(rest_api_id=rest_api_id, user_id=user_id, datetime=datetime_key)
    client.hincrby(redis_key, utc_time_now.hour, 1)


def create_model(cursor, model, type, platform, vendor, user_id):
    cursor.execute(create_model_sql, (model, type, platform, vendor, user_id))
    model_id = cursor.fetchone()[0]
    return model_id


def create_service(cursor, name, url, port, access_token, user_id):
    cursor.execute(create_common_service_sql, (name, url, port, access_token, user_id))
    service_id = cursor.fetchone()[0]
    return service_id


def check_device_bind_model(cursor, uid, mid):
    cursor.execute(query_device_owner_by_mid_sql, (mid,))
    ids = cursor.fetchall()
    for _id in ids:
        if _id != uid:
            return True
        else:
            continue
    return False
