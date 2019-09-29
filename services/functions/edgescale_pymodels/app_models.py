# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
import os
import unicodedata

import requests
from sqlalchemy import Integer, text, String, JSON, DateTime, Boolean, SmallInteger, Text, Date, func
from sqlalchemy.orm import relationship

from edgescale_pymodels.constants import CERTS, HEADERS, RESOURCE_GET_APPSUM
from edgescale_pymodels import constants
from edgescale_pymodels import tag_models
from edgescale_pymodels import device_models
from edgescale_pymodels.base_model import *
from edgescale_pyutils.exception_utils import InvalidParameterException


class AppVolumeMakerMixin(object):
    @classmethod
    def parse_volumes(cls, volumes):
        """
        "dynamic_volumes": [{"hostPath": {"path": ""}, "name": ""}],
        "dynamic_volumeMounts": [{"readOnly": true, "mountPath": "", "name": ""}]
        """
        if not volumes:
            return constants.EMPTY_VOLUMES_MAPPING, \
                   constants.EMPTY_VOLUME_MOUNTS_MAPPING
        elif not isinstance(volumes, list):
            raise InvalidParameterException('Invalid volumes type, not list.')
        elif len(volumes) == 1 \
                and volumes[0]['hostPath'].strip() == '' \
                and volumes[0]['mountPath'].strip() == '':
            return constants.EMPTY_VOLUMES_MAPPING, \
                   constants.EMPTY_VOLUME_MOUNTS_MAPPING

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


class AppCommandsMixin(object):
    @classmethod
    def jsonfy_commands(cls, commands):
        if not commands:
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


class AppArgsMixin(object):
    @classmethod
    def jsonfy_args(cls, args):
        if not args:
            args = ''
        elif isinstance(args, list):
            args = json.dumps(args)
        elif isinstance(args, str):
            args = args.strip()
            args = json.dumps([args])

        return args

    @classmethod
    def param_resources_filter(cls, resource):
        limits = {}
        if not resource:
            return
        try:
            if 'cpu' in resource:
                float(resource['cpu'])
                limits['cpu'] = resource['cpu']
        except Exception:
            raise InvalidParameterException('cpu should be float')

        try:
            if 'memory' in resource:
                # backcompatible database
                if 'M' in resource['memory']:
                    resource['memory'] = resource['memory']\
                        .split('M')[0]
                int(resource['memory'])
                # resource unit is MiByte
                limits['memory'] = resource['memory'] + "Mi"
        except Exception:
            raise InvalidParameterException('memory should be int')
        return limits

    @classmethod
    def param_env_filter(cls, env):
        ret = []
        if env and isinstance(env, list):
            for e in env:
                if 'name' in e and "value" in e:
                    if e["name"].strip() != "":
                        ret.append({"name": e["name"], "value": e["value"]})
                else:
                    raise InvalidParameterException('env should use keys name and value')
        return ret


class DccaAppInstance(Base):
    __tablename__ = 'dcca_app_instances'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_app_inst_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)
    config = Column(JSON)
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    softapp_id = Column(ForeignKey('dcca_softapps.id'), nullable=False)
    device_id = Column(ForeignKey('hosts.id'), nullable=False)
    create_date = Column(DateTime, server_default=text("now()"))

    device = relationship('Host')
    owner = relationship('DccaUser')
    softapp = relationship('DccaSoftapp')


class DccaAppMirror(Base):
    __tablename__ = 'dcca_app_mirror'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_app_mirror_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    description = Column(String(128))
    user_id = Column(ForeignKey('dcca_users.id'))

    user = relationship('DccaUser')

    @classmethod
    def query_by_id(cls, _id):
        return session.query(cls).filter(
            or_(
                and_(
                    cls.id == _id, cls.user == ctx.current_user
                ),
                and_(
                    cls.id == _id, cls.is_public.is_(True)
                )
            )).one()


class DccaApplication(OutputMixin, Base, GetterMethodMixin):
    __tablename__ = 'dcca_applications'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_applications_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)
    display_name = Column(String(64))
    description = Column(String(256))
    likes = Column(Integer, server_default=text("0"))
    stars = Column(SmallInteger, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    vendor_id = Column(ForeignKey('dcca_vendors.id'))
    logical_delete_flag = Column(Boolean, nullable=False, server_default=text("false"))
    image = Column(String(256))
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    owner_id = Column(ForeignKey('dcca_users.id'))
    documents = Column(Text)
    in_store = Column(Boolean, server_default=text("false"))

    owner = relationship('DccaUser')
    vendor = relationship('DccaVendor')
    tags = relationship('DccaTag', secondary='dcca_ass_app_tag')
    softapps = relationship('DccaSoftapp', back_populates='application')

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).filter(
                and_(
                    cls.id == _id,
                    cls.logical_delete_flag.is_(False),
                    cls.owner == ctx.current_user
                )).one()
        except NoResultFound:
            return None

    @classmethod
    def full_image(cls, username, image_name):
        if not image_name:
            return ''
        else:
            return os.path.join(constants.IMAGE_ROOT, username, image_name)

    @classmethod
    def query_all(cls, limit=20, offset=0):
        query_set = session.query(cls).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.logical_delete_flag.is_(False)
            )
        ).outerjoin(DccaSoftapp).filter(cls.id == DccaSoftapp.application_id)

        total = query_set.count()
        apps = query_set.limit(limit).offset(offset).all()
        return apps, total

    @classmethod
    def query_by_tags(cls, tags, limit=100, offset=0):
        tag_list = tag_models.DccaTag.query_in_name(tags)

        query_set = session.query(cls) \
            .outerjoin(t_dcca_ass_app_tag) \
            .filter(
            and_(
                cls.owner == ctx.current_user,
                cls.logical_delete_flag.is_(False),
                t_dcca_ass_app_tag.c.tag_id.in_([t.id for t in tag_list])
            ))

        total = query_set.count()
        apps = query_set.limit(limit).offset(offset).all()
        return apps, total

    @classmethod
    def authorized(cls, app_id):
        app = cls.get(app_id)
        if app.owner == ctx.current_user or app.is_public or app.in_store:
            return True
        else:
            return False

    @classmethod
    def query_by_name(cls, name):
        try:
            return session.query(cls).filter(and_(
                func.lower(cls.name) == name.lower(),
                cls.owner == ctx.current_user,
                cls.logical_delete_flag.is_(False))).all()
        except NoResultFound:
            return None

    @classmethod
    def get_app_statistics(cls, host, port, params):
        url = RESOURCE_GET_APPSUM.format(dns=host, port=port, uid=ctx.current_user.id)
        try:
            # Fetch app sum
            resp = requests.get(url, params=params, cert=CERTS, headers=HEADERS, verify=False, timeout=7)
        except requests.Timeout:
            raise Exception('The k8s timeout exception.')
        if resp.status_code != 200:
            raise Exception(resp.content)

        result = []
        if isinstance(resp.content, str):
            appsum = json.loads(resp.content)
            while appsum and len(appsum) > 0:
                v = appsum.pop()
                app = cls.query_by_name(v["name"])
                # Fill app id
                if app:
                    v['app_id'] = app[len(app)-1].id

                # Init total number
                devices = []

                # Filter devices and remove other users devices
                for dev in v['items']:
                    devinfo = {}
                    device = device_models.Host.query_by_name(dev['deviceid'])
                    # Device is not found
                    if not device:
                        devinfo['id'] = ""
                        devinfo['name'] = dev['deviceid']
                        devinfo['created_at'] = dev['appcreatetime']

                        devinfo['mode'] = {}
                        m = dev['deviceid'].split('.')
                        devinfo['mode']['model'] = m[1]
                        devinfo['mode']['type'] = m[2]
                        devinfo['mode']['platform'] = m[3]
                        devinfo['mode']['vendor'] = m[4]
                    else:
                        # Fill device info
                        devinfo['id'] = device.id
                        devinfo['name'] = device.name
                        devinfo['created_at'] = datetime.strftime(device.created_at, '%Y-%m-%d %H:%M:%S')
                        devinfo['display_name'] = device.display_name

                        devinfo['mode'] = {}
                        devinfo['mode']['model'] = device.model.model
                        devinfo['mode']['type'] = device.model.type
                        devinfo['mode']['platform'] = device.model.platform
                        devinfo['mode']['vendor'] = device.model.vendor

                    devices.append(devinfo)

                if v.get('total', 0) > 0:
                    v['items'] = devices
                    result.append(v)

        return result


class DccaApplyApp(Base):
    __tablename__ = 'dcca_apply_apps'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_apply_apps_id_seq'::regclass)"))
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    approved = Column(Boolean, server_default=text("false"))
    comments = Column(Text)
    app_id = Column(ForeignKey('dcca_applications.id'))
    op_times = Column(SmallInteger, server_default=text("0"))
    status = Column(SmallInteger, server_default=text("0"))

    app = relationship('DccaApplication')
    user = relationship('DccaUser')


class DccaSoftapp(GetterMethodMixin, AppCommandsMixin, AppArgsMixin, AppVolumeMakerMixin, Base):
    __tablename__ = 'dcca_softapps'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_softapps_id_seq'::regclass)"))
    name = Column(String(32))
    version = Column(String(20), nullable=False)
    mirror_id = Column(ForeignKey('dcca_app_mirror.id'), nullable=False)
    image_name = Column(String(64))
    application_id = Column(ForeignKey('dcca_applications.id'))
    commands = Column(String(512))
    args = Column(String(512))
    hostnetwork = Column(Boolean, server_default=text("false"))
    ports = Column(JSON)
    volumes = Column(JSON)
    volume_mounts = Column(JSON)
    cap_add = Column(Boolean, nullable=False, server_default=text("false"))
    morepara = Column(JSON)

    application = relationship('DccaApplication', back_populates='softapps')
    registry = relationship('DccaAppMirror')

    @classmethod
    def query_one(cls, app_id, version):
        try:
            return session.query(cls).filter(
                and_(cls.application_id == app_id, cls.version == version)
            ).limit(1).one()
        except NoResultFound:
            return None


class DccaSoftware(Base):
    __tablename__ = 'dcca_softwares'

    swid = Column(Integer, primary_key=True, server_default=text("nextval('softwares_swid_seq'::regclass)"))
    version_id = Column(ForeignKey('dcca_sw_versions.id'), nullable=False)
    date = Column(Date, server_default=text("('now'::text)::date"))
    url = Column(String(1024), nullable=False)
    name = Column(String(30))

    version = relationship('DccaSwVersion')


class DccaSwVersion(Base):
    __tablename__ = 'dcca_sw_versions'

    id = Column(Integer, primary_key=True, server_default=text("nextval('sw_versions_id_seq'::regclass)"))
    major = Column(String(20), nullable=False)
    minor = Column(String(20), nullable=False)
