# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify
import uuid

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.param_utils import validate_resource, validate_envrionment, check_json
from edgescale_pyutils.redis_utils import connect_redis
from edgescale_pyutils.view_utils import get_oemid, get_json
from model import K8S_PORT, _DNS, REDIS_HOST, REDIS_PORT, REDIS_PWD, SHORT_REST_API_ID
from model.constants import *
from utils import *

deployment_bp = Blueprint("deployment", __name__)


@deployment_bp.route("/applications", methods=["GET"])
def query_all_user_k8s_pods():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    params = {
        'taskid': request.args.get('taskid', ""),
        'status': request.args.get('status', ""),
        'device': request.args.get('device', ""),
        'limit': request.args.get('limit', 0),
        'offset': request.args.get('offset', 0)
    }
    result = query_k8s_pods(request.cursor, RESOURCE_GET_STATUS.format(dns=_DNS, port=K8S_PORT, uid=uid), uid, params=params)
    return jsonify(result)


@deployment_bp.route("/applications", methods=["POST"])
def deploy_app_container():
    """
    Deploy an APP in k8s
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    # TESTED: This is on the dev server to support to start task
    deploy = get_json(request).get("deploy", {})
    app_id = deploy.get('application_id')
    version = deploy.get('version')
    device_id = deploy.get('device_id')
    secret = deploy.get('secret')  # not transform
    task_id = None
    task_owner_id = deploy.get('user_id')  # not transform

    parameters = get_json(request).get("parameters", {})
    # dynamic arguments
    dynamic_commands = parameters.get('dynamic_commands')
    dynamic_args = parameters.get('dynamic_args')
    dynamic_host_network = parameters.get('dynamic_host_network')  # not transform
    dynamic_ports = parameters.get('dynamic_ports')
    dynamic_volumes = parameters.get('dynamic_volumes')
    dynamic_resources = parameters.get('dynamic_resources')
    dynamic_env = parameters.get('dynamic_env')

    # dynamic_volumeMounts = event.get('dynamic_volumeMounts')
    dynamic_cap_add = parameters.get('dynamic_cap_add')

    if not device_id:
        return jsonify({
            'status': 'fail',
            'message': 'Device ID cannot be empty.'
        })

    if not app_id:
        return jsonify({
            'status': 'fail',
            'message': 'Application ID cannot be empty'
        })

    if not version:
        return jsonify({
            'status': 'fail',
            'message': 'The "version" cannot be empty.'
        })

    # Check if the device owner
    if secret == 'nocheckOwner$':
        task_id = deploy.get('task_id')
        uid = task_owner_id
    else:
        if not uid:
            return jsonify({
                'status': 'fail',
                'message': 'The uid cannot be empty.'
            })

        is_owner = check_devices_owner(request.cursor, uid, device_id)
        if not is_owner:
            return jsonify({
                'status': 'fail',
                'message': 'Not authorized device exist'
            })

    if check_exceed_max_limit(request.cursor, uid, RESOURCE_GET_STATUS.format(dns=_DNS, port=K8S_PORT, uid=uid))['exceed_max']:
        return jsonify({
            'status': 'fail',
            'message': 'Cannot deploy, you have exceeded the maxinum number that can deploy'
        })

    # Check if exceed the max install limit of per-time
    client = connect_redis(REDIS_HOST, port=REDIS_PORT, pwd=REDIS_PWD)
    result = check_exceed_per_time_max_limit(request.cursor, client, user_id=uid,
                                             limit_type_id=LIMIT_TYPE_ID_MAX_PER_SEC_INSTALL,
                                             res_key=DEPLOY_APP_KEY_INSTALL)
    if result['status'] == 'fail':
        return jsonify(result)

    request.cursor.execute(query_device_by_id_sql, (device_id,))
    device_name = request.cursor.fetchone()[0]

    request.cursor.execute(select_softapps_sql, (app_id, version))
    softapp = request.cursor.fetchone()

    if softapp is None:
        return jsonify({
            'status': 'fail',
            'message': 'No such application'
        })

    softapp = AppInstance._make(softapp)
    app_name = '{name}-{hex}'.format(name=softapp.app_name.strip().lower(),
                                     hex=uuid.uuid4().hex)

    registry = softapp.registry
    image = softapp.image

    # Handle dynamic arguments
    if dynamic_commands:
        commands = jsonfy_commands(dynamic_commands)
    else:
        commands = r'{}'.format(softapp.commands) if softapp.commands else None

    if dynamic_args:
        args = jsonfy_args(dynamic_args)
    else:
        args = r'{}'.format(softapp.args) if softapp.args else None

    if dynamic_host_network:
        _hostNetwork = dynamic_host_network
    else:
        _hostNetwork = True if softapp.hostnetwork else False
    validate_host_network(_hostNetwork)

    if dynamic_ports:
        _ports = dynamic_ports
    else:
        _ports = softapp.ports if softapp.ports else []
    _ports = validate_ports(_ports)

    if dynamic_volumes:
        _volumes, _volumeMounts = validate_volumes_v2(dynamic_volumes)
    else:
        _volumes = _volumeMounts = None

    if dynamic_cap_add:
        _cap_add = dynamic_cap_add
    else:
        _cap_add = softapp.cap_add
    validate_cap_add(_cap_add)

    if dynamic_resources:
        _resources = validate_resource(dynamic_resources)
    elif softapp.morepara:
        _resources = validate_resource(softapp.morepara.get('resources'))
    else:
        _resources = None

    if dynamic_env:
        _env = validate_envrionment(dynamic_env)
    elif softapp.morepara:
        _env = validate_envrionment(softapp.morepara.get('env'))
    else:
        _env = []
    # Append default envrionment
    _env.append({"name": "ES_DEVICEID", "value": device_name})

    def _template(is_hub):
        o = json.loads(container_template)
        o['metadata']['name'] = app_name
        o['metadata']['labels']['name'] = app_name
        o['spec']['containers'][0]['name'] = app_name
        o['spec']['containers'][0]['imagePullPolicy'] = 'Always'
        if is_hub:
            o['spec']['containers'][0]['image'] = '{image}:{version}'.format(image=image, version=version)
        else:
            o['spec']['containers'][0]['image'] = '{registry}/{image}:{version}'.format(registry=registry, image=image,
                                                                                        version=version)

        o['spec']['nodeSelector']['kubernetes.io/hostname'] = device_name

        if commands and len(commands) > 0:
            o['spec']['containers'][0]['command'] = json.loads(commands)

        if args and len(args) > 0:
            o['spec']['containers'][0]['args'] = json.loads(args)

        if _hostNetwork:
            o['spec']['hostNetwork'] = True
        else:
            o['spec']['hostNetwork'] = False

        if _ports:
            o['spec']['containers'][0]['ports'] = _ports
            o['spec']['hostNetwork'] = False

        if _volumes:
            o['spec']['volumes'] = _volumes

        if _volumeMounts:
            o['spec']['containers'][0]['volumeMounts'] = _volumeMounts

        if _cap_add:
            o['spec']['containers'][0]['securityContext']['capabilities'] = {'add': []}
            o['spec']['containers'][0]['securityContext']['capabilities']['add'].append("NET_ADMIN")

        if _resources:
            o['spec']['containers'][0]['resources'] = {'limits': _resources}

        if _env:
            o['spec']['containers'][0]['env'] = _env
        return json.dumps(o)

    try:
        headers = {
            'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

        # print('curl -k -v --cert ./admin.pem --key ./admin-key.pem'
        #       ' -XPOST'
        #       ' -H "Accept: application/json"'
        #       ' -H "Content-Type: application/json"'
        #       ' -H "User-Agent: kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01"'
        #       ' "https://ec2-35-160-45-56.us-west-2.compute.amazonaws.com:6443/api/v1/namespaces/default/pods"'
        #       ' -d \'{template}\''.format(template=_template(False)))

        if registry == 'hub.docker.com':
            tpl = _template(True)
        else:
            tpl = _template(False)

        resp = requests.post(RESOURCE_DEPLOY_APP.format(dns=_DNS, port=K8S_PORT, uid=uid),
                             data=tpl, cert=certs, headers=headers, verify=False, timeout=7)

        raw_k8s_result = resp.content.decode("utf-8")
        parsed_k8s_result = k8s_filter(raw_k8s_result)

        try:
            # event, template, raw_k8s_result, parsed_k8s_result, resource
            event = {
                  "admin": request.headers.get("admin"),
                  "uid": uid,
                  "device_id": device_id,
                  "version": version,
                  "app_id": app_id,
                  "dynamic_commands": dynamic_commands,
                  "dynamic_args": dynamic_args,
                  "dynamic_ports": dynamic_ports,
                  "dynamic_volumes": dynamic_volumes,
                  "dynamic_cap_add": dynamic_cap_add
            }
            request.cursor.execute(create_deploy_record_sql, (json.dumps(event), tpl, raw_k8s_result,
                                                              json.dumps(parsed_k8s_result),
                                                              RESOURCE_DEPLOY_APP.format(dns=_DNS, port=K8S_PORT, uid=uid),
                                                              task_id, device_id))
        except Exception:
            import traceback
            traceback.print_exc()
            raise DCCAException('Fail to upload deploy record')
        else:
            request.conn.commit()
            make_record_deploy_times(client, SHORT_REST_API_ID, user_id=uid)

        return jsonify(parsed_k8s_result)
    except Exception as e:
        return jsonify({
            'error': True,
            'status': 'fail',
            'message': '{}'.format(str(e))
        })


@deployment_bp.route("/applications", methods=["DELETE"])
def remove_app_by_names():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    app_name_list = get_json(request).get('names', [])

    client = connect_redis(REDIS_HOST, port=REDIS_PORT, pwd=REDIS_PWD)
    result = check_exceed_per_time_max_limit(request.cursor, client, user_id=uid,
                                             limit_type_id=LIMIT_TYPE_ID_MAX_PER_SEC_UNINSTALL,
                                             res_key=DEPLOY_APP_KEY_UNINSTALL)

    if result['status'] == 'fail':
        return jsonify(result)

    results = []
    for app_name in app_name_list:
        headers = {
            'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

        data = '{"kind":"DeleteOptions", "apiVersion":"v1", "gracePeriodSeconds":0}'
        resource = RESOURCE_DELETE_APP_V2.format(dns=_DNS, port=K8S_PORT, uid=uid, app_name=app_name)
        resp = requests.delete(resource, data=data, cert=certs, headers=headers, verify=False, timeout=7)
        results.append(json.loads(resp.content))

    return jsonify(results)


@deployment_bp.route("/applications/params", methods=["POST"])
def check_deploy_params():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    parameters = get_json(request).get("parameters", {})
    # dynamic arguments
    dynamic_host_network = parameters.get('dynamic_host_network')
    dynamic_ports = parameters.get('dynamic_ports')
    dynamic_volumes = parameters.get('dynamic_volumes')
    dynamic_cap_add = parameters.get('dynamic_cap_add')

    # Handle dynamic arguments
    validate_host_network(dynamic_host_network)

    if dynamic_ports:
        validate_ports(dynamic_ports)

    if dynamic_volumes:
        validate_volumes_v2(dynamic_volumes)

    validate_cap_add(dynamic_cap_add)

    return jsonify({
        'status': 'success',
        'message': 'Valid parameters'
    })


@deployment_bp.route("/applications/<app_name>/conlog", methods=["GET"])
def get_app_conlog(app_name):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    headers = {
        'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
        'Accept': '*/*'
    }

    res = RESOURCE_GET_APP_CONLOG.format(dns=_DNS, port=K8S_PORT, uid=uid, app_name=app_name)
    resp = requests.get(res, headers=headers, cert=certs, verify=False, timeout=10)
    if resp.status_code > 210:
        raise DCCAException("app response error: %s" % resp.status_code)

    return jsonify(resp.content.decode("utf-8"))


@deployment_bp.route("/applications/<app_name>/history", methods=["GET"])
def get_app_eventlog(app_name):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    headers = {
        'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
        'Accept': '*/*'
    }

    res = RESOURCE_GET_APP_EVENT.format(dns=_DNS, port=K8S_PORT, uid=uid, app_name=app_name)
    resp = requests.get(res, headers=headers, cert=certs, verify=False, timeout=10)
    if resp.status_code > 210:
        raise DCCAException("app response error: %s" % resp.status_code)

    return jsonify(resp.content.decode("utf-8"))


@deployment_bp.route("/applications/<app_name>/reboot", methods=["POST"])
def reboot_app(app_name):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    headers = {
        'User-Agent': 'kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01',
        'Accept': '*/*'
    }

    res = RESOURCE_POST_APP_REBOOT.format(dns=_DNS, port=K8S_PORT, uid=uid, app_name=app_name)
    resp = requests.post(res, headers=headers, cert=certs, verify=False, timeout=10)
    return jsonify(k8s_filter(resp.content))
