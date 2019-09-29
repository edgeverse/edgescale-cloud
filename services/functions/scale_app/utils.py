# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import json
import unicodedata
from collections import OrderedDict
from datetime import datetime

from sqlalchemy.dialects import postgresql

from edgescale_pyutils.exception_utils import InvalidParameterException, EdgeScaleException
from model.raw_sqls import *
from model.constants import *


def strftime(time):
    return datetime.strftime(time, TIME_FORMAT_STR)


def check_app_owner(cursor, app_id, uid, include_store=False):
    if include_store:
        cursor.execute(count_app_owner_include_store_sql, (app_id, uid))
    else:
        cursor.execute(count_app_owner_sql, (app_id, uid))

    count = cursor.fetchone()[0]
    if count:
        return True
    else:
        return False


def check_app_in_store(cursor, app_id):
    cursor.execute(count_app_in_store_sql, (app_id,))
    count = cursor.fetchone()[0]
    if count:
        return True
    else:
        return False


def full_image_path(username, image_name):
    if image_name:
        return os.path.join(IMAGE_ROOT, username, image_name)
    else:
        return None


def query_user_name(cursor, uid):
    cursor.execute(query_name_sql, (uid,))
    username = cursor.fetchone()[0]

    return username


def app_json_maker(app, username):
    application = ApplicationShort._make(app)
    app = application._asdict()

    app_owner = app['owner']
    app['image'] = full_image_path(app_owner, app['image'])

    if username == app_owner:
        app['is_owner'] = True
    else:
        app['is_owner'] = False

    del app['owner']

    return app


def check_app(cursor, name, uid, include_store=False):
    cursor.execute(count_app_owner_name_sql, (name, uid))
    count = cursor.fetchone()[0]

    if count:
        return True
    else:
        return False


def query_app_tags(cursor, app_id):
    cursor.execute(query_app_tags_sql, (app_id, ))
    tags = cursor.fetchall()

    data = []
    for tag in tags:
        data.append({
            'id': tag[0],
            'name': tag[1]
        })
    return data


def parse_app_data(cursor, uid, apps):
    data = OrderedDict()
    data['limit'] = 0
    data['offset'] = 0
    data['total'] = 0

    data['applications'] = []

    username = query_user_name(cursor, uid)

    def make_app_json(app):
        application = Application._make(app)
        app = application._asdict()
        app['image'] = full_image_path(app['owner'], app['image'])

        if app['owner'] == username:
            app['is_owner'] = True
        else:
            app['is_owner'] = False
        del app['owner']

        app['tags'] = query_app_tags(cursor, (app['id'], ))
        return app

    for result in apps:
        data['applications'].append(make_app_json(result))

    return data


def validate_ports(ports):
    if not isinstance(ports, list):
        raise InvalidParameterException('Invalid port type')
    elif not ports:
        return EMPTY_PORTS_MAPPING
    elif len(ports) == 1 \
        and 'hostPort' in ports[0] and 'containerPort' in ports[0] \
        and ports[0]['hostPort'] == '' and ports[0]['containerPort'] == '':
        return EMPTY_PORTS_MAPPING
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
    if not volumes:
        return EMPTY_VOLUMES_MAPPING, \
               EMPTY_VOLUME_MOUNTS_MAPPING
    elif not isinstance(volumes, list):
        raise InvalidParameterException('Invalid volumes type, not list.')
    elif len(volumes) == 1 \
            and volumes[0]['hostPath'].strip() == '' \
            and volumes[0]['mountPath'].strip() == '':
        return EMPTY_VOLUMES_MAPPING, \
               EMPTY_VOLUME_MOUNTS_MAPPING

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


def validate_cap_add(cap_add):
    if cap_add is None or cap_add == '':
        pass
    elif not isinstance(cap_add, bool):
        raise InvalidParameterException('The "cap_add" should be a boolean type.')


def jsonfy_commands(commands):
    if isinstance(commands, int):
        commands = str(commands)

    if not commands:
        commands = ''
    elif isinstance(commands, list):
        commands = json.dumps(commands)
    elif isinstance(commands, str):
        commands = commands.strip()
        if commands.isdigit():
            commands = json.dumps(commands.split(' '))

        try:
            c = json.loads(commands)
            if isinstance(c, list):
                commands = json.dumps([unicodedata.normalize('NFKD', s).encode('utf8', 'ignore') for s in c])
        except ValueError:
            commands = json.dumps(commands.split(' '))

    return commands


def jsonfy_args(args):
    if isinstance(args, int):
        args = str(args)

    if not args:
        args = ''
    elif isinstance(args, list):
        args = json.dumps(args)
    elif isinstance(args, str):
        args = args.strip()
        args = json.dumps([args])

    return args


def check_image_owner(cursor, app_id, image_id, uid):
    cursor.execute(count_docker_image_sql, (uid, app_id, image_id))
    count = cursor.fetchone()[0]
    if count:
        return True
    else:
        return False


def remove_docker_image(cursor, image_id):
    cursor.execute(remove_docker_image_sql, (image_id, ))


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


def create_tag(cursor, tag_name):
    create_tag_command = create_tag_sql.format(name=tag_name)
    cursor.execute(create_tag_command)
    tag_id = cursor.fetchone()[0]

    return tag_id


def check_application_id(application_id):
    if not application_id:
        raise EdgeScaleException('Application id can not be empty')
    else:
        return None
