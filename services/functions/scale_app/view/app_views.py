# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify
from sqlalchemy.orm.attributes import flag_modified

from edgescale_pymodels.app_models import DccaApplication, DccaSoftapp, DccaAppMirror
from edgescale_pymodels.user_models import DccaUser
from edgescale_pyutils.exception_utils import DCCAException
from edgescale_pyutils.model_utils import ctx
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.param_utils import validate_resource, validate_envrionment, check_json, check_tag_name
from model import session, K8S_HOST, K8S_PORT
from utils import *
from model import IS_DEBUG
from model.ischema import *

app_bp = Blueprint("application", __name__)


@app_bp.route("/<app_id>", methods=["GET"])
def query_one_app(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_app_owner(request.cursor, app_id, uid, include_store=True):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    request.cursor.execute(query_app_by_id_sql, (app_id,))
    app = request.cursor.fetchone()

    username = query_user_name(request.cursor, uid)

    return jsonify(app_json_maker(app, username))


@app_bp.route("/<app_id>", methods=["PUT"])
def modify_application(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not isinstance(app_id, int):
        if not app_id.isdigit():
            return jsonify({
                'status': 'fail',
                'message': 'The application ID must be a digit.'
            })

    if not check_app_owner(request.cursor, app_id, uid):
        return jsonify({
            'status': 'fail',
            'message': 'Not device owner, access deny'
        })

    check_json(request)
    application = get_json(request).get("application", {})
    name = application.get('name')
    display_name = application.get('display_name')
    description = application.get('description')
    image = application.get('image')
    public = application.get('public')

    modify_items = OrderedDict()
    if name or name is None:
        modify_items['name'] = name

    if display_name or display_name is None:
        modify_items['display_name'] = display_name

    if description or description is None:
        modify_items['description'] = description

    if image or image is None:
        modify_items['image'] = image

    if public is True:
        modify_items['is_public'] = True
    elif public is False:
        modify_items['is_public'] = False

    if len(modify_items) == 0:
        return jsonify({
            'status': 'fail',
            'message': 'You need to provide what going to modify supplied. '
                       'including "name", "display_name", or "description".'
        })
    else:
        update_app_cmd = 'UPDATE dcca_applications SET '
        update_val = []
        for _name, _value in list(modify_items.items()):
            update_app_cmd += ' {}=%s,'.format(_name)
            update_val.append(_value)

        update_app_cmd = update_app_cmd.rstrip(',')
        update_app_cmd += ' WHERE id={};'.format(app_id)

    try:
        request.cursor.execute(update_app_cmd, tuple(update_val))
        request.conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'Application has been updated'
        })
    except Exception:
        if IS_DEBUG:
            import traceback
            traceback.print_exc()
        raise DCCAException('Error when update APP information')


@app_bp.route("/<app_id>", methods=["DELETE"])
def delete_application(app_id):
    """
        Remove the application from APP store
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_app_owner(request.cursor, app_id, uid):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    try:
        request.cursor.execute(logical_delete_app_sql, (app_id, ))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to delete application.')

    return jsonify({
        'status': 'success',
        'message': 'Success to delete the application'
    })


@app_bp.route("/<app_id>/documents", methods=["GET"])
def query_app_document(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_app_owner(request.cursor, app_id, uid, include_store=True):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    request.cursor.execute(query_app_doc_sql, (app_id,))
    documents = request.cursor.fetchone()

    return jsonify(documents[0])


@app_bp.route("/<app_id>/documents", methods=["PUT"])
def create_app_document(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    documents = get_json(request).get('documents')
    if not check_app_owner(request.cursor, app_id, uid):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    try:
        request.cursor.execute(update_app_doc_sql, (documents, app_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception: fail to update documents')

    return jsonify({
        'status': 'success',
        'message': 'Success to update APP documents'
    })


@app_bp.route("/<app_id>/documents/temp", methods=["GET"])
def query_app_document_temp(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_app_owner(request.cursor, app_id, uid, include_store=True):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    request.cursor.execute(query_app_doc_sql, (app_id,))
    documents = request.cursor.fetchone()

    return jsonify(documents[0])


@app_bp.route("/<app_id>/documents/temp", methods=["PUT"])
def create_app_document_temp(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    documents = get_json(request).get('documents')
    if not check_app_owner(request.cursor, app_id, uid):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    try:
        request.cursor.execute(update_app_doc_sql, (documents, app_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Exception: fail to update documents')

    return jsonify({
        'status': 'success',
        'message': 'Success to update APP documents'
    })


@app_bp.route("/<app_id>/images", methods=["GET"])
def query_softapp_by_app_id(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_app_owner(request.cursor, app_id, uid):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    request.cursor.execute(query_softapps_sql, (app_id,))
    softapps = request.cursor.fetchall()

    results = {
        'total': 0,
        'images': []
    }

    for sa in softapps:
        _sa = AppShort._make(sa)

        softapp = AppObj(
            _sa.id, _sa.version, _sa.registry_id, _sa.image_name, _sa.commands, _sa.args,
            AppArguments(_sa.host_network, _sa.ports, _sa.volumes, _sa.volume_mounts,
                         _sa.cap_add, _sa.morepara)._asdict()
        )

        _softapp = softapp._asdict()
        if softapp.commands:
            _softapp['commands'] = ' '.join(json.loads(softapp.commands))

        if softapp.args:
            _softapp['args'] = ' '.join(json.loads(softapp.args))

        parsed_volumes = {}
        volumes = softapp.arguments['volumes']
        volume_mounts = softapp.arguments['volume_mounts']
        if volumes:
            for i in range(len(volumes)):
                v_name = volumes[i]['name']
                if v_name not in parsed_volumes:
                    parsed_volumes[v_name] = {
                        'hostPath': volumes[i]['hostPath']['path']
                    }
                else:
                    parsed_volumes[v_name]['hostPath'] = volumes[i]['hostPath']['path']

                vm_name = volume_mounts[i]['name']
                if vm_name not in parsed_volumes:
                    parsed_volumes[vm_name] = {
                        'mountPath': volume_mounts[i]['mountPath'],
                        'mountPathReadOnly': volume_mounts[i]['readOnly']
                    }
                else:
                    parsed_volumes[vm_name]['mountPath'] = volume_mounts[i]['mountPath']
                    parsed_volumes[vm_name]['mountPathReadOnly'] = volume_mounts[i]['readOnly']

            del _softapp['arguments']['volumes']
            del _softapp['arguments']['volume_mounts']
            _softapp['arguments']['volumes'] = list(parsed_volumes.values())
        else:
            del _softapp['arguments']['volumes']
            del _softapp['arguments']['volume_mounts']
            _softapp['arguments']['volumes'] = PARSED_PATH_MAPPING
        # if morepara is not None
        if softapp.arguments.get('morepara'):
            resources = softapp.arguments['morepara'].get('resources')
            envrionment = softapp.arguments['morepara'].get('env')
            if resources:
                _softapp['arguments']['resources'] = resources
            if envrionment:
                _softapp['arguments']['env'] = envrionment
            del softapp.arguments['morepara']

        results['images'].append(_softapp)

    results['total'] = len(softapps)

    return jsonify(results)


@app_bp.route("/<app_id>/images", methods=["POST"])
def add_app_container_info(app_id):
    """
    Create one softapp record with given parameters (Create the information of docker image)
    """
    check_json(request)
    # TESTED: This works for creating docker image in DB
    # TODO if not user's application, cannot add image item.
    image = get_json(request).get('image', {})
    registry_id = image.get('registry_id') if image.get('registry_id') else DEFAULT_REGISTRY_ID
    image_name = image.get('image_name')
    version = image.get('version')
    application_id = image.get('application_id')

    commands = image.get('commands')
    args = image.get('args')

    def _dumps(obj):
        return json.dumps(obj)

    # TODO check all the arguments are valid
    arguments = get_json(request).get("arguments", {})
    # Net work arguments
    hostNetwork = True if arguments.get('hostNetwork') else False

    # Ports arguments
    ports = arguments.get('ports') if arguments.get('ports') else []
    ports = validate_ports(ports)
    ports = _dumps(ports)

    # Volumes arguments
    volumes = arguments.get('volumes') if arguments.get('volumes') else None
    _volumes, _volumeMounts = validate_volumes_v2(volumes)
    _volumes = _dumps(_volumes)
    _volumeMounts = _dumps(_volumeMounts)

    # The cap_add flag
    capAddFlag = True if arguments.get('capAdd') else False
    validate_cap_add(capAddFlag)

    morepara = {}
    res = arguments.get('resources')
    resources = validate_resource(res)
    if resources:
        morepara['resources'] = resources

    env = arguments.get('env')
    env = validate_envrionment(env)
    if env:
        morepara['env'] = env

    morepara = _dumps(morepara)

    if not registry_id:
        return jsonify({
            'error': True,
            'status': 'fail',
            'message': 'The registry id cannot be empty'
        })

    if not image_name:
        return jsonify({
            'error': True,
            'status': 'fail',
            'message': 'The image name cannot be empty'
        })

    if not version:
        return jsonify({
            'error': True,
            'status': 'fail',
            'message': 'The version cannot be empty'
        })

    try:
        request.cursor.execute(select_softapp_sql, (registry_id, image_name, version, application_id))
        softapps = request.cursor.fetchall()
        if softapps:
            return jsonify({
                'status': 'fail',
                'message': 'The version({}) already exist'.format(version)
            })
    except Exception:
        raise DCCAException('Error to query application image')

    try:
        request.cursor.execute(select_application_sql, (application_id,))
        count = request.cursor.fetchone()[0]
        if count == 0:
            return jsonify({
                'status': 'fail',
                'message': 'The given application ID not exist'
            })
    except Exception:
        raise DCCAException('Error to count application')

    commands = jsonfy_commands(commands)
    args = jsonfy_args(args)

    try:
        request.cursor.execute(insert_softapp_sql, (version, registry_id, image_name, application_id,
                                                    commands, args, hostNetwork, ports,
                                                    _volumes, _volumeMounts, capAddFlag, morepara))
        image_id = request.cursor.fetchone()[0]

        request.conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'Success to add application instance',
            'image_id': image_id
        })
    except Exception as e:
        err_msg = 'Fail to create application image.'
        if IS_DEBUG:
            err_msg += str(e)
        raise DCCAException(err_msg)


@app_bp.route("/<app_id>/images/<image_id>", methods=["PUT"])
def modify_docker_image(app_id, image_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)

    image = get_json(request).get("image", {})
    registry_id = image.get('registry_id')
    image_name = image.get('image_name')
    version = image.get('version')
    commands = image.get('commands')
    args = image.get('args')

    arguments = get_json(request).get("arguments", {})
    hostnetwork = arguments.get('hostNetwork')
    ports = arguments.get('ports')
    volumes = arguments.get('volumes')
    cap_add = arguments.get('capAdd')
    resources = arguments.get('resources')
    env = arguments.get('env')

    app = DccaApplication.query_by_id(app_id)
    if not app:
        return jsonify({
            'status': 'fail',
            'message': 'The application not exist or cannot access'
        })

    softapp = DccaSoftapp.get(image_id)
    if not softapp:
        return jsonify({
            'status': 'fail',
            'message': 'The docker image not exist or cannot access'
        })

    # Mirror is registry, "hub.docker.com" for example
    if registry_id:
        registry = DccaAppMirror.query_by_id(registry_id)
        if not registry:
            return jsonify({
                'status': 'fail',
                'message': 'The registry not accessable'
            })
        softapp.registry = registry

    # The image name, "arm64v8/busybox" for example
    if image_name:
        softapp.image_name = image_name

    if version:
        softapp.version = version

    if commands or commands == '':
        softapp.commands = DccaSoftapp.jsonfy_commands(commands)

    if args or args == '':
        softapp.args = DccaSoftapp.jsonfy_args(args)

    if isinstance(hostnetwork, bool):
        softapp.hostnetwork = hostnetwork

    if ports:
        softapp.ports = ports

    if volumes:
        _volumes, _volume_mounts = DccaSoftapp.parse_volumes(volumes)
        softapp.volumes = _volumes
        softapp.volume_mounts = _volume_mounts

    if resources or env:
        # Backcompatible
        if not isinstance(softapp.morepara, dict):
            _morepara = {}
        else:
            _morepara = softapp.morepara

        if resources:
            _morepara['resources'] = DccaSoftapp.param_resources_filter(resources)

        if env:
            _morepara['env'] = DccaSoftapp.param_env_filter(env)
        flag_modified(softapp, 'morepara')
        softapp.morepara = _morepara

    softapp.cap_add = True if cap_add else False

    try:
        session.add(softapp)
        session.commit()
    except Exception:
        raise DCCAException('Fail to modify app image')

    return jsonify({
        'status': 'success',
        'message': 'Success to update application docker image',
    })


@app_bp.route("/<app_id>/images/<image_id>", methods=["DELETE"])
def remove_docker_image_view(app_id, image_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_image_owner(request.cursor, app_id, image_id, uid):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    try:
        remove_docker_image(request.cursor, image_id)
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to remove docker image')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove docker image.'
    })


@app_bp.route("/<app_id>/store", methods=["POST"])
def apply_for_store(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    comments = get_json(request).get('comments')

    if not check_app_owner(request.cursor, app_id, uid):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_OWNER
        })

    try:
        request.cursor.execute(apply_app_sql, (uid, comments, app_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to apply for public request')

    return jsonify({
        'status': 'success',
        'message': 'Success to make a shown in store request'
    })


@app_bp.route("/<app_id>/versions", methods=["GET"])
def query_app_version(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    if not check_app_owner(request.cursor, app_id, uid, include_store=True):
        if not check_app_in_store(request.cursor, app_id):
            return jsonify({
                'status': 'fail',
                'message': MSG_NOT_APP_OWNER
            })

    try:
        request.cursor.execute(query_image_versions_sql, (app_id,))
        results = request.cursor.fetchall()
        versions = [version[0] for version in results]
        data = {'versions': versions}

        return jsonify(data)
    except Exception:
        raise DCCAException('Error: get version by id')


@app_bp.route("", methods=["GET"])
def get_all():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    # is_public = request.args.get('is_public')  # TODO not support this now
    limit = request.args.get('limit') if request.args.get('limit') else 10
    offset = request.args.get('offset') if request.args.get('offset') else 0

    apps, total = DccaApplication.query_all(limit, offset)

    data = []
    for app in apps:
        item = app.as_dict(schema=AppSchema)
        item['image'] = app.full_image(app.owner.username, app.image)
        item['tags'] = [{'id': t.id, 'name': t.name} for t in app.tags]
        item['version'] = [s.version for s in app.softapps]
        data.append(item)

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['total'] = total
    results['applications'] = data

    return jsonify(results)


@app_bp.route("", methods=["POST"])
def create_app_image():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    application_info = get_json(request).get("application", {})
    name = application_info.get('name')
    display_name = application_info.get('display_name')
    description = application_info.get('description')
    image_name = application_info.get('image')

    if not name:
        return jsonify({
            'status': 'fail',
            'message': 'The "name" cannot be empty.'
        })

    if not image_name:
        image_name = IMAGE_DEFAULT_NAME

    try:
        request.cursor.execute(create_app_item_sql, (name, display_name, description, image_name, False, uid,))
        request.conn.commit()
    except Exception:
        raise DCCAException('Error to insert commodity')

    application_id = request.cursor.fetchone()[0]
    return jsonify({
        'status': 'success',
        'app_id': application_id,
        'message': 'Success to add an application record'
    })


@app_bp.route("/copy", methods=["POST"])
def store_to_my_app():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    app_id = get_json(request).get('app_id')

    request.cursor.execute(query_app_id_store_sql, (app_id,))
    app = request.cursor.fetchone()

    if not app:
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP
        })

    app = ApplicationShort._make(app)
    name = app.name
    display_name = app.display_name
    description = app.description
    image = "../%s/%s" % (app.owner, app.image)

    if check_app(request.cursor, name, uid, include_store=False):
        return jsonify({
            'status': 'fail',
            'message': MSG_NOT_APP_NAME
        })

    try:
        request.cursor.execute(create_app_item_sql, (name, display_name, description, image, True, uid))
    except Exception:
        raise DCCAException('Error to insert commodity')

    application_id = request.cursor.fetchone()[0]

    request.cursor.execute(query_softapps_sql, (app_id,))
    softapps = request.cursor.fetchall()
    for sa in softapps:
        _sa = AppShort._make(sa)
        registry_id = _sa.registry_id if _sa.registry_id else DEFAULT_REGISTRY_ID
        image_name = _sa.image_name
        version = _sa.version
        commands = _sa.commands
        args = _sa.args
        hostNetwork = _sa.host_network
        ports = json.dumps(_sa.ports)
        capAddFlag = _sa.cap_add
        _volumes = json.dumps(_sa.volumes)
        _volumeMounts = json.dumps(_sa.volume_mounts)

        try:
            request.cursor.execute(select_softapp_sql, (registry_id, image_name, version, application_id))
            softapps = request.cursor.fetchall()
            if softapps:
                return jsonify({
                    'status': 'fail',
                    'message': 'The version({}) already exist'.format(version)
                })
        except Exception:
            raise DCCAException('Error to query application image')

        try:
            request.cursor.execute(insert_softapp_sql_v0, (version, registry_id, image_name, application_id,
                                                           commands, args, hostNetwork, ports,
                                                           _volumes, _volumeMounts, capAddFlag))
            request.conn.commit()
        except Exception as e:
            err_msg = 'Fail to create application image.'
            if IS_DEBUG:
                err_msg += str(e)
            raise DCCAException(err_msg)

    return jsonify({
        'status': 'success',
        'app_id': application_id,
        'message': 'Success to add application record to my app'
    })


@app_bp.route("/filter", methods=["GET"])
def query_app_by_tags_blured_filter():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') if request.args.get('limit') else 200
    offset = request.args.get('offset') if request.args.get('offset') else 0
    tag_names_str = request.args.get('tag_names')

    _tags = tag_names_str.split(',')
    apps, total = DccaApplication.query_by_tags(_tags, limit, offset)

    data = OrderedDict()
    data['applications'] = []
    data['limit'] = limit
    data['offset'] = offset
    data['total'] = total

    for app in apps:
        data['applications'].append(app.as_dict(schema=AppSchema))

    return jsonify(data)


@app_bp.route("/mirrors", methods=["GET"])
def query_mirrors():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin', False) == 'true' else False

    query_mirrors_command = query_mirror_sql

    if not is_admin:
        condition = f"WHERE is_public IS TRUE OR user_id={uid}"
        query_mirrors_command = query_mirror_sql.replace(';', ' ') + condition + ';'

    request.cursor.execute(query_mirrors_command)
    mirrors = request.cursor.fetchall()
    results = {"mirrors": []}

    for mir in mirrors:
        mir = Mirror._make(mir)
        results['mirrors'].append(mir._asdict())

    return jsonify(results)


@app_bp.route("/requests", methods=["GET"])
def query_all_app_requests():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    is_admin = True if request.headers.get('admin', False) == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': 'Not admin, have no access permission'
        })

    limit = request.args.get('limit') or 20
    offset = request.args.get('offset') or 0
    filter_text = request.args.get('filter_text')
    order_by = request.args.get('order_by') or "id"
    order_type = request.args.get('order_type') or 'desc'

    _filter = ""
    if filter_text:
        _filter = "WHERE U.username LIKE '%{}%'".format(filter_text)

    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['orderBy'] = order_by
    results['orderType'] = order_type
    results['results'] = []

    request.cursor.execute(count_total_apply_apps_sql.format(filter=_filter))
    results['total'] = request.cursor.fetchone()[0]

    order_by = "R." + order_by
    query_all_apply_items = query_all_apply_items_sql.format(filter=_filter,
                                                             order_by=order_by,
                                                             order_type=order_type,
                                                             limit=limit,
                                                             offset=offset)
    request.cursor.execute(query_all_apply_items)
    AppRequests = namedtuple('AppRequests', ['id', 'username', 'app_name', 'created_at',
                                             'comments', 'approved', 'status'])
    app_requests = request.cursor.fetchall()

    for req in app_requests:
        req = AppRequests._make(req)._asdict()
        req['created_at'] = strftime(req['created_at'])
        if req['status']:
            req['status'] = True
        else:
            req['status'] = False

        results['results'].append(req)

    return jsonify(results)


@app_bp.route("/requests/<request_id>", methods=["PUT"])
def handle_the_in_store_request(request_id):
    """
        Admin can approve user's request
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    approve = get_json(request).get('approve')

    is_admin = True if request.headers.get('admin', False) == 'true' else False
    if not is_admin:
        return jsonify({
            'status': 'fail',
            'message': 'Not admin, have no access permission'
        })

    request.cursor.execute(query_req_info_sql, (request_id,))
    req_info = request.cursor.fetchone()
    if not req_info:
        return jsonify({
            'status': 'fail',
            'message': 'Request not exist.'
        })

    app_id = req_info[0]

    try:
        request.cursor.execute(update_apply_status_sql, (approve, AUDIT_REQUEST_STATUS, request_id))
    except Exception:
        raise DCCAException('Fail to update apply status')

    tof = 'True' if approve else 'False'
    try:
        request.cursor.execute(update_in_store_status_sql, (tof, app_id))
    except Exception:
        raise DCCAException('Fail to update device status')

    try:
        request.cursor.execute(update_app_permission_sql, (tof, app_id))
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to update app permission')

    approve_status = 'approve' if approve else 'deny'
    return jsonify({
        'status': 'success',
        'message': f'Success to {approve_status} the request'
    })


@app_bp.route("/statistics", methods=["GET"])
def query_app_statistics():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    params = {
        "limit": request.args.get('limit', 10),
        "offset": request.args.get('offset', 0),
        "appname": request.args.get('appname', ""),
        "device": request.args.get('device', "")
    }

    ctx.current_user = DccaUser.get_by_id(uid)
    return DccaApplication.get_app_statistics(K8S_HOST, K8S_PORT, params)


@app_bp.route("/store", methods=["GET"])
def query_all_store_apps():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    limit = request.args.get('limit') if request.args.get('limit') else 20
    offset = request.args.get('offset') if request.args.get('offset') else 0

    request.cursor.execute(count_all_store_apps_sql)
    total = request.cursor.fetchone()[0]

    # cursor.execute(query_all_store_apps_sql.format(limit=limit, offset=offset))
    request.cursor.execute(query_all_store_apps_sql, (limit, offset))
    apps = request.cursor.fetchall()

    data = parse_app_data(request.cursor, uid, apps)
    data['limit'] = limit
    data['offset'] = offset
    data['total'] = total
    return jsonify(data)


@app_bp.route("/tags", methods=["GET"])
def query_application_tags():
    application_ids_str = request.args.get('app_ids')

    conditions = ''
    application_ids = application_ids_str.split(',')
    for index, app_id in enumerate(application_ids):
        if index == 0:
            conditions += ' A.id={}'.format(app_id)
        else:
            conditions += ' OR A.id={}'.format(app_id)

    query_application_tags_cmd = query_application_tags_sql.format(conditions=conditions)
    request.cursor.execute(query_application_tags_cmd)
    tag_items = request.cursor.fetchall()

    results = {'items': {}}
    for tag_item in tag_items:
        tag_item = ApplicationTag._make(tag_item)
        app_id = tag_item.app_id
        tag_id = tag_item.tag_id
        tag_name = tag_item.tag_name
        if app_id not in results['items']:
            results['items'][app_id] = [{
                'id': tag_id,
                'name': tag_name
            }]
        else:
            results['items'][app_id].append({
                'id': tag_id,
                'name': tag_name
            })

    return jsonify(results)


@app_bp.route("/<app_id>/tags", methods=["POST"])
def attach_tag_to_applications(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    tag_name = get_json(request).get('name')

    check_tag_name(tag_name)

    tag_id = query_tag(request.cursor, tag_name)
    if not tag_id:
        tag_id = create_tag(request.cursor, tag_name)

    attach_tag_to_app_cmd = attach_tag_to_app_sql.format(app_id=app_id, tag_id=tag_id)
    try:
        request.cursor.execute(attach_tag_to_app_cmd)
    except Exception:
        raise DCCAException('Fail to attach tag to application!')

    request.conn.commit()
    return jsonify({
        'status': 'success',
        'message': 'Success attached "{}" to application'.format(tag_name)
    })


@app_bp.route("/<app_id>/tags", methods=["DELETE"])
def remove_tag_from_application(app_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    tag_name = get_json(request).get('name')

    check_tag_name(tag_name)
    check_application_id(app_id)

    remove_tag_from_app_cmd = remove_tag_from_app_sql.format(application_id=app_id, tag_name=tag_name)
    try:
        request.cursor.execute(remove_tag_from_app_cmd)
    except Exception:
        raise DCCAException('Fail to remove tag from application')

    request.conn.commit()
    return jsonify({
        'status': 'success',
        'message': 'Success to remove tag "{}" from application'.format(tag_name)
    })
