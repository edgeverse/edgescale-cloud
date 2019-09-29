# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8

from datetime import datetime
from collections import OrderedDict
import json
import uuid
import unicodedata

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, \
    Index, Integer, JSON, SmallInteger, String, Table, Text, UniqueConstraint, text, func, or_, and_, desc
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
import boto3
import requests

from ischema import ModelEngineSchema, TemplateAppSchema
from utils import ctx, DCCAException
from constants import *


Session = sessionmaker(autoflush=False)
session = scoped_session(sessionmaker())

Base = declarative_base()
metadata = Base.metadata


def nested_getattr(obj, attr, **kwargs):
    attributes = attr.split('.')
    for i in attributes:
        try:
            obj = getattr(obj, i)
            if callable(obj):
                obj = obj()
        except AttributeError:
            if kwargs.has_key('default'):
                return kwargs['default']
            else:
                raise
    return obj


class GetterMethodMixin(object):
    @classmethod
    def get(cls, id):
        try:
            return session.query(cls).filter(cls.id == id).one()
        except NoResultFound:
            return None


class QueryTaskInstLOMixin(object):
    @classmethod
    def task_inst(cls, task, limit=5000, offset=0):
        return session.query(cls).filter(cls.task==task).all()


class QueryByIDMixin(object):
    def query_by_id(cls, id):
        try:
            return session.query(cls).filter(and_(cls.id == id, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None


class QueryTaskInstMixin(object):
    @classmethod
    def query_inst(cls, task):
        return session.query(cls).filter(cls.task==task).all()


class QueryTaskDeviceMixin(object):
    @classmethod
    def query_devices(cls, task):
        devices = set()
        instances = cls.query_inst(task)
        for inst in instances:
            devices.add(inst.device)
        return devices


class OutputMixin(object):
    RELATIONSHIPS_TO_DICT = False

    def __iter__(self):
        return self.to_dict().iteritems()

    def as_dict(self, schema=None):
        if not schema:
            raise Exception('Schema cannot be empty.')

        instance = schema()

        res = OrderedDict()
        for attr, field in instance.fields.iteritems():
            attr_name = field.metadata.get('attr')
            if not attr_name:
                attr_name = attr

            attr_value = nested_getattr(self, attr_name)

            filter_func = field.metadata.get('func')
            if filter_func:
                attr_value = filter_func(attr_value)

            res[attr] = attr_value

        return res

    def to_dict(self, rel=None, backref=None, whitelist=None):
        whitelist = {} if whitelist is None else whitelist
        if rel is None:
            rel = self.RELATIONSHIPS_TO_DICT

        res = OrderedDict()
        for attr, column in self.__mapper__.c.items():
            if attr not in whitelist.keys():
                continue

            value = getattr(self, attr)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')

            res[attr] = value

        if rel:
            for attr, relation in self.__mapper__.relationships.items():
                # Avoid recursive loop between to tables.
                if backref == relation.table:
                    continue
                value = getattr(self, attr)
                if value is None:
                    res[relation.key] = None
                elif isinstance(value.__class__, DeclarativeMeta):

                    res[relation.key] = value.to_dict(backref=self.__table__)
                else:
                    res[relation.key] = [i.to_dict(backref=self.__table__)
                                         for i in value]
        return res

    def to_json(self, rel=None):
        def extended_encoder(x):
            if isinstance(x, datetime):
                return x.isoformat()
            if isinstance(x, UUID):
                return str(x)
        if rel is None:
            rel = self.RELATIONSHIPS_TO_DICT
        return json.dumps(self.to_dict(rel), default=extended_encoder)


class QueryInIdLogicalMinx(object):
    @classmethod
    def query_in(cls, ids):
        return session.query(cls).filter(
            and_(cls.id.in_(ids),
                 cls.owner==ctx.current_user,
                 cls.logical_delete==False
                 )).all()


class EsTaskHelperMinxin(object):
    @classmethod
    def _container_template(cls):
        return {"apiVersion":"v1", "kind":"Pod", "metadata":{"name":"<app_name>","labels":{"name":"<app_name>"}},"spec":{"hostNetwork":True,"containers":[{"name":"<app_name>","image":"<docker_repo/app_name:version>","imagePullPolicy":"IfNotPresent","securityContext":{"privileged":True}}],"nodeSelector":{"kubernetes.io/hostname":"<device_id>"},"imagePullSecrets":[{"name":"secret"}]}}

    def _mk_name(self):
        return '{name}-{hex}'.format(name=self.softapp.application.name.strip().lower(),
                                     hex=uuid.uuid4().hex)

    @classmethod
    def _jsonfy_commands(cls, commands):
        if not commands:
            commands = ''
        elif isinstance(commands, list):
            commands = json.dumps(commands)
        elif isinstance(commands, basestring):
            commands = commands.strip()
            try:
                c = json.loads(commands)
                if isinstance(c, list):
                    commands = json.dumps(map(lambda s: unicodedata.normalize('NFKD', s).encode('utf8', 'ignore'), c))
            except ValueError:
                commands = json.dumps(commands.split(' '))
        return commands

    @classmethod
    def jsonfy_args(cls, args):
        if not args:
            args = ''
        elif isinstance(args, list):
            args = json.dumps(args)
        elif isinstance(args, basestring):
            args = args.strip()
            args = json.dumps([args])

        return args

    @classmethod
    def is_valid_parameter(cls, parameter, name):
        if name in parameter and parameter[name]:
            return True
        else:
            return False

    def _param_commands_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_commands'):
            return self._jsonfy_commands(self.payload['parameters'].get('dynamic_commands'))
        else:
            return r'{}'.format(self.softapp.commands) if self.softapp.commands else None
    def _param_args_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_args'):
            return self._jsonfy_args(self.payload['parameters'].get('dynamic_args'))
        else:
            return r'{}'.format(self.softapp.args) if self.softapp.args else None
    def _param_host_network_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_host_network'):
            return True if self.payload['parameters'].get('dynamic_host_network') else False
        else:
            return self.softapp.hostnetwork
    def _param_ports_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_ports'):
            return self.payload['parameters'].get('dynamic_ports')
        else:
            return self.softapp.ports
    def _param_cap_add_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_cap_add'):
            return self.payload['parameters'].get('dynamic_cap_add')
        else:
            return self.softapp.cap_add

    def _param_volumns_filter_v0(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_volumes'):
            return self.payload['parameters'].get('dynamic_volumes')
        else:
            return self.softapp.get('dynamic_volumes')
    def _param_volumn_mounts_filter_v0(self):
        if self.is_valid_parameter(self.payload['parameters'], ''):
            pass # TODO
    def _param_volumns_filter(self):
        """
        "dynamic_volumes": [{"hostPath": {"path": ""}, "name": ""}],
        "dynamic_volumeMounts": [{"readOnly": true, "mountPath": "", "name": ""}]
        """
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_volumes'):
            volumes = self.payload['parameters'].get('dynamic_volumes')

        # dynamic_volumes, dynamic_volumeMounts
        dynamic_volumes = []
        dynamic_volume_mounts = []
        for _index, volume in enumerate(volumes):
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

    def _template_maker(self):
        o = self._container_template()
        name = self._mk_name()
        image_name = self.softapp.image_name
        version = self.softapp.version
        registry = self.softapp.mirror.name
        if registry == 'hub.docker.com':
            is_docker_hub = True
        else:
            is_docker_hub = False

        # The parameters filter
        commands = self._param_commands_filter()
        args = self._param_args_filter()
        host_network = self._param_host_network_filter()
        ports = self._param_ports_filter()
        volumes, volume_mounts = self._param_volumns_filter()   # TODO
        cap_add = self._param_cap_add_filter()

        o['metadata']['name'] = name
        o['metadata']['labels']['name'] = name
        o['spec']['containers'][0]['name'] = name
        o['spec']['containers'][0]['imagePullPolicy'] = 'Always'
        if is_docker_hub:
            o['spec']['containers'][0]['image'] = '{image}:{version}'.format(image=image_name, version=version)
        else:
            o['spec']['containers'][0]['image'] = '{registry}/{image}:{version}'.format(registry=registry,
                                                                                        image=image_name,
                                                                                        version=version)

        o['spec']['nodeSelector']['kubernetes.io/hostname'] = self.device.name

        if commands:
            o['spec']['containers'][0]['command'] = json.loads(commands)

        if args:
            o['spec']['containers'][0]['args'] = json.loads(args)

        if host_network:
            o['spec']['hostNetwork'] = True
        else:
            o['spec']['hostNetwork'] = False

        if ports:
            o['spec']['containers'][0]['ports'] = ports
            o['spec']['hostNetwork'] = False

        if volumes:
            o['spec']['volumes'] = volumes

        if volume_mounts:
            o['spec']['containers'][0]['volumeMounts'] = volume_mounts

        if cap_add:
            o['spec']['containers'][0]['securityContext']['capabilities'] = {'add': []}
            o['spec']['containers'][0]['securityContext']['capabilities']['add'].append("NET_ADMIN")

        return json.dumps(o)

    def _deploy_url_maker(self, host, port):
        return RESOURCE_DEPLOY_APP.format(dns=host, port=port, uid=self.task.owner.id)

    def _query_url_maker(self, host, port, name):
        return RESOURCE_QUERY_APP_STATUS.format(dns=host, port=port, uid=self.task.owner.id, name=name)

    @classmethod
    def _k8s_filter(cls, content):
        if isinstance(content, basestring):
            ps = json.loads(content)
        else:
            ps = content

            # Return if http code is not 0
        if ps.has_key('code') and ps['code'] != 0:
            # print "skip to parse the error message"
            # Handle error situation

            d = OrderedDict()
            d['code'] = ps.get('code')
            d['apiVersion'] = 'v1'
            d['error'] = ps.get('error')
            d['message'] = ps.get('message')
            return d

        d = OrderedDict()
        d['code'] = 0
        d['apiVersion'] = 'v1'
        d['items'] = ps.get('items')
        return d

    @classmethod
    def _status_filter(cls, status):
        if status == 'Pending':
            return DA_TASK_STATUS_PENDING
        elif status == 'Creating':
            return DA_TASK_STATUS_CREATING
        elif status == 'Starting':
            return DA_TASK_STATUS_STARTING
        elif status == 'Failed':
            return DA_TASK_STATUS_FAILED
        elif status == 'Running':
            return DA_TASK_STATUS_RUNNING
        elif status == 'Deleting':
            return DA_TASK_STATUS_DELETING
        elif status == 'Deleted':
            return DA_TASK_STATUS_DELETED
        else:
            return DA_TASK_STATUS_UNKNOWN


class DccaAccessRecord(Base):
    __tablename__ = 'dcca_access_records'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_access_records_id_seq'::regclass)"))
    uid = Column(Integer)
    username = Column(String(255))
    is_admin = Column(Integer)
    auth_at = Column(DateTime, server_default=text("now()"))
    method_arn = Column(String(256))


class DccaAccountType(Base):
    __tablename__ = 'dcca_account_types'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_account_type_id_seq'::regclass)"))
    name = Column(String(16), nullable=False, unique=True)
    description = Column(String(32))
    is_external = Column(Boolean, nullable=False, server_default=text("true"))


class DccaAccount(Base):
    __tablename__ = 'dcca_accounts'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_accounts_id_seq'::regclass)"))
    company_name = Column(String(32))
    telephone = Column(String(16))
    email = Column(String(32), nullable=False, unique=True)
    job_title = Column(String(32))
    account_type_id = Column(ForeignKey(u'dcca_account_types.id'))
    first_name = Column(String(16))
    last_name = Column(String(16))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    status = Column(Integer, nullable=False, server_default=text("0"))

    account_type = relationship('DccaAccountType')


class DccaApiAccessRecord(Base):
    __tablename__ = 'dcca_api_access_records'
    __table_args__ = (
        Index('dcca_api_access_records_user_id_access_date_index', 'user_id', 'access_date'),
    )

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_api_access_records_id_seq'::regclass)"))
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    access_date = Column(Date)
    record = Column(JSON)

    user = relationship('DccaUser')


class DccaAppInstance(Base):
    __tablename__ = 'dcca_app_instances'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_app_inst_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)
    config = Column(JSON)
    owner_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    softapp_id = Column(ForeignKey(u'dcca_softapps.id'), nullable=False)
    device_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    create_date = Column(DateTime, server_default=text("now()"))

    device = relationship('Host')
    owner = relationship('DccaUser')
    softapp = relationship('DccaSoftapp')


class DccaAppMirror(Base):
    __tablename__ = 'dcca_app_mirror'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_app_mirror_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    description = Column(String(128))
    user_id = Column(ForeignKey(u'dcca_users.id'))

    user = relationship('DccaUser')


class DccaApplication(Base, GetterMethodMixin):
    __tablename__ = 'dcca_applications'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_applications_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)
    display_name = Column(String(64))
    description = Column(String(256))
    likes = Column(Integer, server_default=text("0"))
    stars = Column(SmallInteger, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    vendor_id = Column(ForeignKey(u'dcca_vendors.id'))
    logical_delete_flag = Column(Boolean, nullable=False, server_default=text("false"))
    image = Column(String(256))
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    owner_id = Column(ForeignKey(u'dcca_users.id'))
    documents = Column(Text)
    in_store = Column(Boolean, server_default=text("false"))

    owner = relationship('DccaUser')
    vendor = relationship('DccaVendor')
    tags = relationship('DccaTag', secondary=u'dcca_ass_app_tag')


class DccaApplyApp(Base):
    __tablename__ = 'dcca_apply_apps'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_apply_apps_id_seq'::regclass)"))
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    approved = Column(Boolean, server_default=text("false"))
    comments = Column(Text)
    app_id = Column(ForeignKey(u'dcca_applications.id'))
    op_times = Column(SmallInteger, server_default=text("0"))
    status = Column(SmallInteger, server_default=text("0"))

    app = relationship('DccaApplication')
    user = relationship('DccaUser')


t_dcca_ass_app_tag = Table(
    'dcca_ass_app_tag', metadata,
    Column('application_id', ForeignKey(u'dcca_applications.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey(u'dcca_tags.id'), primary_key=True, nullable=False)
)


t_dcca_ass_device_tag = Table(
    'dcca_ass_device_tag', metadata,
    Column('device_id', ForeignKey(u'hosts.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey(u'dcca_tags.id'), primary_key=True, nullable=False)
)


class DccaAssDeviceTask(Base):
    __tablename__ = 'dcca_ass_device_task'

    device_id = Column(ForeignKey(u'hosts.id'), primary_key=True, nullable=False)
    task_id = Column(ForeignKey(u'edgescale_tasks.id'), primary_key=True, nullable=False)
    status_payload = Column(JSON)
    status = Column(SmallInteger, nullable=False, server_default=text("0"))

    device = relationship('Host')
    task = relationship('EdgescaleTask')


class DccaAssHostModel(Base):
    __tablename__ = 'dcca_ass_host_model'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_ass_host_model_id_seq'::regclass)"))
    host_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    model_id = Column(ForeignKey(u'dcca_models.id'), nullable=False)

    host = relationship('Host')
    model = relationship('DccaModel')


t_dcca_ass_model_service = Table(
    'dcca_ass_model_service', metadata,
    Column('model_id', ForeignKey(u'dcca_models.id'), primary_key=True, nullable=False),
    Column('service_id', ForeignKey(u'dcca_services.id'), primary_key=True, nullable=False)
)


t_dcca_ass_model_softapp = Table(
    'dcca_ass_model_softapp', metadata,
    Column('model_id', ForeignKey(u'dcca_models.id'), nullable=False),
    Column('softapp_id', ForeignKey(u'dcca_softapps.id'), nullable=False),
    Index('dcca_ass_model_softapp_model_id_softapp_id_uindex', 'model_id', 'softapp_id', unique=True)
)


class DccaAssModelSoftware(Base):
    __tablename__ = 'dcca_ass_model_software'

    model_id = Column(ForeignKey(u'dcca_models.id'), nullable=False)
    software_id = Column(ForeignKey(u'dcca_softwares.swid'), nullable=False)
    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_ass_model_software_id_seq'::regclass)"))

    model = relationship('DccaModel')
    software = relationship('DccaSoftware')


t_dcca_ass_role_perm = Table(
    'dcca_ass_role_perm', metadata,
    Column('role_id', ForeignKey(u'dcca_roles.id'), primary_key=True, nullable=False),
    Column('perm_id', ForeignKey(u'dcca_permissions.id'), primary_key=True, nullable=False)
)


class DccaAssSolutionImage(Base):
    __tablename__ = 'dcca_ass_solution_images'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_ass_solution_images_id_seq'::regclass)"))
    solution = Column(String(64), nullable=False)
    model_id = Column(ForeignKey(u'dcca_models.id'), nullable=False)
    image = Column(Text, nullable=False)
    version = Column(String(64), nullable=False)
    link = Column(Text, nullable=False)
    is_public = Column(Boolean, server_default=text("true"))
    in_s3 = Column(Boolean, server_default=text("true"))
    public_key = Column(Text)
    is_signed = Column(Boolean, server_default=text("false"))
    logical_delete_flag = Column(Boolean, server_default=text("false"))
    owner_id = Column(ForeignKey(u'dcca_users.id'))

    model = relationship('DccaModel', primaryjoin='DccaAssSolutionImage.model_id == DccaModel.id')
    owner = relationship('DccaUser')
    tags = relationship('DccaTag', secondary=u'dcca_ass_solution_tag')
    users = relationship('DccaUser', secondary=u'dcca_ass_user_solution')


t_dcca_ass_solution_tag = Table(
    'dcca_ass_solution_tag', metadata,
    Column('solution_id', ForeignKey(u'dcca_ass_solution_images.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey(u'dcca_tags.id'), primary_key=True, nullable=False)
)


t_dcca_ass_user_device = Table(
    'dcca_ass_user_device', metadata,
    Column('user_id', ForeignKey(u'dcca_users.id'), nullable=False),
    Column('device_id', ForeignKey(u'hosts.id'), nullable=False),
    UniqueConstraint('user_id', 'device_id')
)


class DccaAssUserRole(Base):
    __tablename__ = 'dcca_ass_user_role'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_ass_user_role_id_seq'::regclass)"))
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    role_id = Column(ForeignKey(u'dcca_roles.id'), nullable=False)

    role = relationship('DccaRole')
    user = relationship('DccaUser')

    @classmethod
    def remove(cls, user, role):
        session.query(DccaAssUserRole).filter(and_(DccaAssUserRole.user==user, DccaAssUserRole.role==role)).delete()


t_dcca_ass_user_solution = Table(
    'dcca_ass_user_solution', metadata,
    Column('user_id', ForeignKey(u'dcca_users.id'), primary_key=True, nullable=False),
    Column('solution_id', ForeignKey(u'dcca_ass_solution_images.id'), primary_key=True, nullable=False)
)


t_dcca_ass_user_task = Table(
    'dcca_ass_user_task', metadata,
    Column('user_id', ForeignKey(u'dcca_users.id'), primary_key=True, nullable=False),
    Column('task_id', ForeignKey(u'edgescale_tasks.id'), primary_key=True, nullable=False)
)


t_dcca_ass_user_vendor = Table(
    'dcca_ass_user_vendor', metadata,
    Column('user_id', ForeignKey(u'dcca_users.id'), primary_key=True, nullable=False),
    Column('vendor_id', ForeignKey(u'dcca_vendors.id'), primary_key=True, nullable=False)
)


class DccaCertificate(Base):
    __tablename__ = 'dcca_certificates'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_certificates_id_seq'::regclass)"))
    body = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)
    chain = Column(Text)
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False, unique=True)

    user = relationship('DccaUser')


class DccaCommonService(Base):
    __tablename__ = 'dcca_common_services'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    type = Column(String(32))
    name = Column(String(32))
    url = Column(String(512))
    port = Column(String(5))
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    access_token = Column(String(128))

    user = relationship('DccaUser')


class DccaContinent(Base):
    __tablename__ = 'dcca_continents'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_continents_id_seq'::regclass)"))
    name = Column(String(16), nullable=False)
    short_name = Column(String(2), nullable=False)


class DccaDeployRecored(Base):
    __tablename__ = 'dcca_deploy_recoreds'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_deploy_recoreds_id_seq'::regclass)"))
    event = Column(JSON)
    template = Column(JSON)
    raw_k8s_result = Column(JSON)
    parsed_k8s_result = Column(JSON)
    resource = Column(String(256))
    task_id = Column(ForeignKey(u'edgescale_tasks.id'))
    device_id = Column(ForeignKey(u'hosts.id'))

    device = relationship('Host')
    task = relationship('EdgescaleTask')


class DccaDeviceAttribute(Base):
    __tablename__ = 'dcca_device_attributes'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_device_attributes_id_seq'::regclass)"))
    name = Column(String(24), nullable=False)
    description = Column(String(256))


class DccaDeviceIp(Base):
    __tablename__ = 'dcca_device_ip'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_device_ip_id_seq'::regclass)"))
    ip = Column(String(256))
    country = Column(String(16))
    continent = Column(String(8))
    latitude = Column(Float(53))
    longitude = Column(Float(53))
    device_id = Column(ForeignKey(u'hosts.id'))
    disabled = Column(Boolean, server_default=text("false"))

    device = relationship('Host')


class DccaDeviceNic(Base):
    __tablename__ = 'dcca_device_nics'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_device_nics_id_seq'::regclass)"))
    ip = Column(String(16))
    device_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))

    device = relationship('Host')


class DccaDevicePosition(Base):
    __tablename__ = 'dcca_device_position'

    id = Column(Integer, primary_key=True, unique=True)
    latitude = Column(Float(53))
    longitude = Column(Float(53))
    location_id = Column(ForeignKey(u'dcca_locations.id'))
    continent_id = Column(ForeignKey(u'dcca_continents.id'))
    ip_address = Column(INET)

    continent = relationship('DccaContinent')
    location = relationship('DccaLocation')


class DccaHardware(Base):
    __tablename__ = 'dcca_hardwares'

    hwid = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_hardwares_hwid_seq'::regclass)"))
    name = Column(String(20), server_default=text("NULL::character varying"))
    url = Column(String(1024))


class DccaLocation(Base):
    __tablename__ = 'dcca_locations'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_locations_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)


class DccaModel(Base):
    __tablename__ = 'dcca_models'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('sw_models_id_seq'::regclass)"))
    model = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    platform = Column(String(255), nullable=False)
    vendor = Column(String(255), nullable=False)
    comment = Column(String(512), server_default=text("NULL::character varying"))
    is_public = Column(Boolean, server_default=text("false"))
    owner_id = Column(ForeignKey(u'dcca_users.id'))
    default_solution_id = Column(ForeignKey(u'dcca_ass_solution_images.id'))

    default_solution = relationship('DccaAssSolutionImage', primaryjoin='DccaModel.default_solution_id == DccaAssSolutionImage.id')
    owner = relationship('DccaUser')
    softapps = relationship('DccaSoftapp', secondary=u'dcca_ass_model_softapp')
    services = relationship('DccaService', secondary=u'dcca_ass_model_service')


class DccaOtaStatu(Base):
    __tablename__ = 'dcca_ota_status'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_ota_status_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)


class DccaPermission(OutputMixin, Base):
    __tablename__ = 'dcca_permissions'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_permissions_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)
    resource_type = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))
    resource_id = Column(ForeignKey(u'dcca_resources.id'))
    is_only_admin_allowed = Column(Boolean, nullable=False, server_default=text("false"))

    resource = relationship('DccaResource', primaryjoin='DccaPermission.resource_id==DccaResource.id',
                            back_populates='permission')
    roles = relationship('DccaRole', secondary=u'dcca_ass_role_perm')

    def __init__(self, name, resource_type, resource):
        self.name = name
        self.resource_type = resource_type
        self.resource = resource

    @classmethod
    def get_by_id(cls, perm_id):
        try:
            return session.query(DccaPermission).filter(DccaPermission.id==perm_id).one()
        except NoResultFound:
            return None

    @classmethod
    def exists(cls, name):
        try:
            return session.query(DccaPermission).filter(DccaPermission.name==name).one()
        except NoResultFound:
            return None

    def remove(self):
        session.delete(self)
        session.query(DccaResource).filter(DccaResource.id==self.resource_id).delete()


class DccaProgres(Base):
    __tablename__ = 'dcca_progress'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_progress_id_seq'::regclass)"))
    device_id = Column(Integer, nullable=False)
    label = Column(String(64), nullable=False)
    progress = Column(SmallInteger, nullable=False)
    message = Column(String(256))
    terminated = Column(Boolean, nullable=False, server_default=text("false"))


class DccaResource(OutputMixin, Base):
    __tablename__ = 'dcca_resources'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_resources_id_seq'::regclass)"))
    name = Column(String(32), nullable=False)
    action = Column(String(16), nullable=False)
    url = Column(String(128), nullable=False)
    description = Column(String(128))

    permission = relationship('DccaPermission', primaryjoin='DccaResource.id==DccaPermission.resource_id',
                              uselist=False, back_populates='resource')

    def __init__(self, name, action, url_pattern, description=None):
        self.name = name
        self.action = action.upper()
        self.url = url_pattern
        self.description = description


class DccaRole(OutputMixin, Base):
    __tablename__ = 'dcca_roles'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_roles_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)
    description = Column(Text)

    perms = relationship('DccaPermission', secondary='dcca_ass_role_perm')

    def __init__(self, name, description=None):
        self.name = name
        self.description = description

    def __repr__(self):
        return '{}: <{}>'.format(self.__class__.__name__, self.name)

    @classmethod
    def get_by_id(cls, _id):
        try:
            return session.query(DccaRole).filter(DccaRole.id==_id).one()
        except NoResultFound:
            return None

    @classmethod
    def exists(cls, name):
        if session.query(func.count(DccaRole.id)).filter(DccaRole.name==name).scalar():
            return True
        else:
            return False

    def remove(self):
        t_dcca_ass_role_perm.delete(t_dcca_ass_role_perm.c.role_id == self.id)
        session.query(DccaAssUserRole).filter(DccaAssUserRole.role_id == self.id).delete()
        session.delete(self)


class DccaService(Base):
    __tablename__ = 'dcca_services'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_services_id_seq'::regclass)"))
    uid = Column(String(32), nullable=False, unique=True)
    name = Column(String(32))
    server_certificate_format = Column(Enum(u'pem', name='server_certificate_format'))
    server_certificate_key = Column(String(512))
    connection_url = Column(String(512))
    config = Column(String(1024))
    signing_certificate_format = Column(Enum(u'pem', name='signing_certificate_format'))
    signing_certificate_key = Column(String(512))
    protocal = Column(String(16), nullable=False)
    cipher_suite = Column(String(64), nullable=False)
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)

    user = relationship('DccaUser')


class DccaSoftapp(Base):
    __tablename__ = 'dcca_softapps'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_softapps_id_seq'::regclass)"))
    name = Column(String(32))
    version = Column(String(20), nullable=False)
    mirror_id = Column(ForeignKey(u'dcca_app_mirror.id'), nullable=False)
    image_name = Column(String(64))
    application_id = Column(ForeignKey(u'dcca_applications.id'))
    commands = Column(String(512))
    args = Column(String(512))
    hostnetwork = Column(Boolean, server_default=text("false"))
    ports = Column(JSON)
    volumes = Column(JSON)
    volume_mounts = Column(JSON)
    cap_add = Column(Boolean, nullable=False, server_default=text("false"))

    application = relationship('DccaApplication')
    mirror = relationship(u'DccaAppMirror')


class DccaSoftware(Base):
    __tablename__ = 'dcca_softwares'

    swid = Column(Integer, primary_key=True, server_default=text("nextval('softwares_swid_seq'::regclass)"))
    version_id = Column(ForeignKey(u'dcca_sw_versions.id'), nullable=False)
    date = Column(Date, server_default=text("('now'::text)::date"))
    url = Column(String(1024), nullable=False)
    name = Column(String(30))

    version = relationship('DccaSwVersion')


class DccaSwVersion(Base):
    __tablename__ = 'dcca_sw_versions'

    id = Column(Integer, primary_key=True, server_default=text("nextval('sw_versions_id_seq'::regclass)"))
    major = Column(String(20), nullable=False)
    minor = Column(String(20), nullable=False)


class DccaTagType(Base):
    __tablename__ = 'dcca_tag_types'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_tag_types_id_seq'::regclass)"))
    name = Column(String(32), nullable=False)
    desc = Column(String(128))


class DccaTag(Base):
    __tablename__ = 'dcca_tags'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_tags_id_seq'::regclass)"))
    name = Column(String(16), nullable=False, unique=True)
    description = Column(String(64))


class DccaTaskStatus(Base):
    __tablename__ = 'dcca_task_status'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_task_status_id_seq'::regclass)"))
    name = Column(String(10), nullable=False)


t_dcca_ass_template_device = Table(
    'dcca_ass_template_device', metadata,
    Column('template_id', ForeignKey(u'dcca_task_templates.id'), primary_key=True, nullable=False),
    Column('device_id', ForeignKey(u'hosts.id'), primary_key=True, nullable=False)
)


TEMPLATE_TYPE_APP = 0
TEMPLATE_TYPE_SOLUTION = 1
class DccaTaskTemplate(OutputMixin, Base):
    __tablename__ = 'dcca_task_templates'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    owner_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    category = Column(SmallInteger, nullable=False, server_default=text("0"))
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    name = Column(String(32), nullable=False)
    description = Column(Text, nullable=False)

    owner = relationship(u'DccaUser')
    devices = relationship(
        'Host',
        secondary=t_dcca_ass_template_device
    )

    def __init__(self, name, category, payload, description=''):
        self.owner = ctx.current_user
        self.category = category
        self.name = name
        self.payload = payload
        self.description = description

    def bind_devices(self, devices):
        for device in devices:
            self.devices.append(device)

    def app_schema(self):
        schemas = []
        for pl in self.payload:
            app_id = pl['application_id']
            app = DccaApplication.get(app_id)
            schema = OrderedDict()
            schema['id'] = app_id
            schema['name'] = app.name
            schema['version'] = pl['version']

            schemas.append(schema)

        return schemas

    def solution_schema(self):
        pass

    def object_as_dict(self):
        result = self.as_dict(schema=TemplateAppSchema)
        schema = self.app_schema()
        return {}

    def make_result(self, task):
        app_data = self.app_schema()

        result = OrderedDict()
        result['status'] = 'success'
        result['message'] = 'Success to create task template'
        result['template'] = self.as_dict(schema=TemplateAppSchema)

        # TODO pagination
        result['template']['schema'] = {}
        result['template']['schema']['applications'] = OrderedDict()
        result['template']['schema']['applications']['total'] = len(app_data)
        result['template']['schema']['applications']['offset'] = 0
        result['template']['schema']['applications']['limit'] = len(app_data)
        result['template']['schema']['applications']['items'] = app_data

        # TODO pagination
        result['template']['schema']['devices'] = OrderedDict()
        result['template']['schema']['devices']['total'] = 0
        result['template']['schema']['devices']['offset'] = 0
        result['template']['schema']['devices']['limit'] = 0
        result['template']['schema']['devices']['items'] = 0


    # TODO
    # TODO
    # TODO
    # TODO




class DccaTaskType(Base):
    __tablename__ = 'dcca_task_types'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_task_types_id_seq'::regclass)"))
    name = Column(String(20), nullable=False)


class DccaTask(Base):
    __tablename__ = 'dcca_tasks'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_tasks_id_seq'::regclass)"))
    device_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    start_time = Column(DateTime, nullable=False, server_default=text("now()"))
    end_time = Column(DateTime)
    type_id = Column(ForeignKey(u'dcca_task_types.id'), nullable=False)
    status_id = Column(ForeignKey(u'dcca_task_status.id'), nullable=False)
    solution_id = Column(ForeignKey(u'dcca_ass_solution_images.id'), nullable=False)
    ota_status_id = Column(ForeignKey(u'dcca_ota_status.id'))

    device = relationship('Host')
    ota_status = relationship('DccaOtaStatu')
    solution = relationship('DccaAssSolutionImage')
    status = relationship('DccaTaskStatus')
    type = relationship('DccaTaskType')


class DccaUserLimitType(Base):
    __tablename__ = 'dcca_user_limit_type'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_user_limit_type_id_seq'::regclass)"))
    name = Column(String(32), nullable=False)
    desc = Column(String(64))
    default_max_limit = Column(Integer, nullable=False)
    default_max_sec = Column(Integer)
    is_per_time = Column(Boolean, nullable=False, server_default=text("false"))


class DccaUserLimit(Base):
    __tablename__ = 'dcca_user_limits'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_user_limits_id_seq'::regclass)"))
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False, index=True)
    limit_type_id = Column(Integer, nullable=False)
    max_limit = Column(Integer, nullable=False)
    max_sec = Column(Integer)

    user = relationship('DccaUser')


class DccaUser(OutputMixin, Base):
    __tablename__ = 'dcca_users'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_users_id_seq'::regclass)"))
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255))
    admin = Column(Boolean, server_default=text("false"))
    password_hash = Column(String(128), nullable=False)
    password_salt = Column(String(128), nullable=False)
    mail_enabled = Column(Boolean, server_default=text("false"))
    update_at = Column(DateTime, nullable=False, server_default=text("now()"))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    timezone = Column(String(255))
    is_marketing = Column(Boolean, server_default=text("false"))
    account_type_id = Column(ForeignKey(u'dcca_account_types.id'), server_default=text("4"))
    image = Column(String(256))

    account_type = relationship('DccaAccountType')
    vendors = relationship('DccaVendor', secondary=u'dcca_ass_user_vendor')
    roles = relationship('DccaRole', secondary=u'dcca_ass_user_role')

    @classmethod
    def get_by_id(cls, id):
        try:
            return session.query(DccaUser).filter(DccaUser.id==id).one()
        except NoResultFound:
            return None

    def has_role(self, role):
        if role in self.roles:
            return True
        else:
            return False

    def revoke_role(self, role):
        DccaAssUserRole.remove(self, role)


class DccaVendor(Base):
    __tablename__ = 'dcca_vendors'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_vendor_id_seq'::regclass)"))
    name = Column(String(32), nullable=False, unique=True)
    is_public = Column(Boolean, nullable=False, server_default=text("true"))


class EdgescaleTask(Base):
    __tablename__ = 'edgescale_tasks'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('edgescale_tasks_id_seq'::regclass)"))
    type = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Integer)
    timestamp = Column(DateTime, server_default=text("now()"))
    logical_delete = Column(Boolean, nullable=False, server_default=text("false"))

    # devices = relationship('Host', secondary=u'dcca_ass_device_task')
    devices = relationship('DccaAssDeviceTask', primaryjoin='EdgescaleTask.id==DccaAssDeviceTask.task_id')

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).outerjoin(t_dcca_ass_user_task).filter(cls.id == t_dcca_ass_user_task.c.task_id) \
                        .filter(and_(t_dcca_ass_user_task.c.user_id == ctx.current_user.id,
                                     t_dcca_ass_user_task.c.task_id == _id,
                                     cls.logical_delete == False)).one()
        except NoResultFound:
            return None

    @classmethod
    def binded_devices(cls, task_id):
        return session.query(Host).outerjoin(DccaAssDeviceTask).filter(Host.id==DccaAssDeviceTask.device_id) \
                    .filter(DccaAssDeviceTask.task_id==task_id).all()

    @classmethod
    def query_all_da(cls, limit=2000, offset=0):
        return session.query(cls)\
                .filter(
                    and_(
                        cls.type==TASK_TYPE_APP,
                        ~cls.status.in_(TASK_STATUS_CANCELED, TASK_STATUS_FAIL, TASK_STATUS_COMPLETE),
                        cls.logical_delete==False))\
                .limit(limit).offset(offset).all()


class EsTask(OutputMixin, QueryInIdLogicalMinx, Base):
    __tablename__ = 'es_tasks'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('es_tasks_id_seq'::regclass)"))
    type = Column(SmallInteger, nullable=False, server_default=text("0"))
    status = Column(SmallInteger, nullable=False, server_default=text("0"))
    payloads = Column(JSON, nullable=False)
    owner_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    logical_delete = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    started_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    ended_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))

    owner = relationship(u'DccaUser')

    def __init__(self, type, payloads):
        self.type = type
        self.status = TASK_STATUS_READY
        self.payloads = payloads
        self.owner = ctx.current_user

    @classmethod
    def query_all(cls, status, device_id, limit=20, offset=0, order_by='id', reverse=True):
        if device_id:
            tasks = EsTask.query_by_device(device_id)
            return tasks, len(tasks)

        query_set = session.query(cls).filter(
                        and_(
                            cls.owner==ctx.current_user,
                            cls.logical_delete==False
                        ))

        if status in TASK_STATUS:
            query_set = query_set.from_self().filter(cls.status==status)

        total = query_set.count()
        query_set = query_set.from_self().limit(limit).offset(offset)

        if order_by:
            item = getattr(cls, order_by, cls.id)
            if reverse:
                query_set = query_set.from_self().order_by(desc(item))
            else:
                query_set = query_set.from_self().order_by(item)

        return query_set.all(), total

    @classmethod
    def query_da_many(cls, limit=2000):
        return session.query(cls).filter(
            and_(cls.type==TASK_TYPE_APP,
                 cls.owner == ctx.current_user,
                 cls.logical_delete==False)) \
            .limit(limit).all()

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).filter(and_(cls.id==_id, cls.owner==ctx.current_user, cls.logical_delete == False)).one()
        except NoResultFound:
            return None

    @classmethod
    def exceed_max_limits(cls, es_version):
        _lambda = boto3.client('lambda')
        edge_deploy = _lambda.invoke(FunctionName='scale_deploy',
                                     InvocationType='RequestResponse',
                                     Payload=json.dumps({
                                         "uid": ctx.current_user.id,
                                         "method": "check_exceed_max_limit"
                                     }),
                                     Qualifier=es_version)
        exceed_max_deploy = json.loads(edge_deploy['Payload'].read())
        if exceed_max_deploy['exceed_max']:
            return True
        else:
            return False

    @classmethod
    def sync_owner(cls):
        tasks = session.query(cls).all()
        for task in tasks:
            task.owner = task.users[0]

    @classmethod
    def query_many(cls, limit=20, offset=0):
        query_set = session.query(cls).filter(
                        and_(
                            cls.owner==ctx.current_user,
                            cls.logical_delete==False
                        ))
        size = query_set.count()
        tasks = query_set.limit(limit).offset(offset).all()
        return tasks, size

    @classmethod
    def check_da_payload(cls, payloads):
        unauthorized = []

        for pl in payloads:
            app_id = pl['application_id']
            version = pl['version']
            softapp = DccaSoftapp.query_one(app_id, version)
            if not DccaApplication.authorized(app_id) or not softapp:
                unauthorized.append(app_id)
            else:
                pl['softapp_id'] = softapp.id
        return unauthorized

    @classmethod
    def check_ota_payload(cls, payload):
        solution_id = payload['solution_id']
        solution = DccaAssSolutionImage.query_by_id(solution_id)
        if not solution:
            return False, None
        else:
            return True, solution

    @classmethod
    def create_da_task(cls, payloads):
        return cls(type=TASK_TYPE_APP, payloads=payloads)

    @classmethod
    def create_ota_task(cls, payloads):
        return cls(type=TASK_TYPE_SOLUTION, payloads=payloads)

    def da_inst(self, device, softapp, payload):
        """
        Generate da task instance
        """
        return EsTaskDaInst(self, device, softapp, payload)

    def ota_inst(self, device, solution):
        return EsTaskOtaInst(self, device, solution)

    def query_task_devices(self, ):
        if self.type == TASK_TYPE_APP:
            return EsTaskDaInst.query_devices(self)
        else:
            return EsTaskOtaInst.query_devices(self)

    @classmethod
    def query_by_device(cls, device_id):
        da_tasks = session.query(cls).outerjoin(
                        EsTaskDaInst, cls.id == EsTaskDaInst.task_id
                    ).filter(
                        and_(
                            cls.owner == ctx.current_user,
                            cls.logical_delete == False,
                            EsTaskDaInst.device_id == device_id
                        )
                    ).all()

        ota_tasks = session.query(cls).outerjoin(
                        EsTaskOtaInst, cls.id == EsTaskOtaInst.task_id
                    ).filter(
                        and_(
                            cls.owner == ctx.current_user,
                            cls.logical_delete == False,
                            EsTaskOtaInst.device_id == device_id
                        )
                    ).all()
        return da_tasks + ota_tasks

    @classmethod
    def query_da_tasks(cls, limit=5000, offset=0):
        return session.query(cls).filter(
                    and_(
                        cls.type==TASK_TYPE_APP,
                        cls.status.in_(TASK_STATUS_HEALTHY),
                        cls.logical_delete==False
                    )
                ).limit(limit).offset(offset).all()

    @classmethod
    def parse_status(cls, data):
        schedule = 0
        complete = 0
        for status in data:
            if status in DA_TASK_SCHEDULED:
                schedule += 1
            else:
                complete += 1

        if schedule != 0:
            return TASK_STATUS_SCHEDULED
        else:
            return TASK_STATUS_COMPLETE


class EsTaskDaInst(QueryTaskDeviceMixin, EsTaskHelperMinxin, QueryTaskInstLOMixin, Base):
    __tablename__ = 'es_task_da_inst'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    task_id = Column(ForeignKey(u'es_tasks.id'))
    device_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    softapp_id = Column(ForeignKey(u'dcca_softapps.id'))
    status = Column(SmallInteger, nullable=False, server_default=text("0"))
    status_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, server_default=text("timezone('utc'::text, now())"))
    payload = Column(JSON, nullable=False)

    device = relationship(u'Host')
    task = relationship(u'EsTask')
    softapp = relationship(u'DccaSoftapp')

    def __init__(self, task, device, softapp, payload):
        self.task = task
        self.device = device
        self.softapp = softapp
        self.status = DA_TASK_STATUS_READY
        self.status_payload = {}
        self.payload = payload

    @classmethod
    def query_inst(cls, limit=2000, offset=0):
        return session.query(cls).filter(
                    ~cls.status.in_([DA_TASK_STATUS_FAILED, DA_TASK_STATUS_DELETING,
                                     DA_TASK_STATUS_DELETED, DA_TASK_STATUS_TIMEOUT,
                                     DA_TASK_STATUS_ERROR, DA_TASK_STATUS_K8S_NO_RESPONSE])
                ).limit(limit).offset(offset).all()

    @classmethod
    def query_devices(cls, task):
        devices = set()
        instances = cls.query_inst(task)
        for inst in instances:
            devices.add(inst.device)
        return devices

    def record_deploy_results(self):
        # TODO
        create_deploy_record_sql = '''
        INSERT INTO dcca_deploy_recoreds 
          (event, template, raw_k8s_result, parsed_k8s_result, resource, task_id, device_id) 
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        '''

    def record_deploy_time(self):
        # Record one time in redis
        pass  # TODO

    def start(self, host=None, port=None):
        if not host or not port:
            raise Exception('The k8s host and port are required.')
        t = self._template_maker()
        # print('curl -k -v --cert ./admin.pem --key ./admin-key.pem'
        #       ' -XPOST'
        #       ' -H "Accept: application/json"'
        #       ' -H "Content-Type: application/json"'
        #       ' -H "User-Agent: kubectl/v1.7.0 (linux/amd64) kubernetes/d3ada01"'
        #       ' "https://ec2-35-160-45-56.us-west-2.compute.amazonaws.com:6443/api/v1/namespaces/default/pods"'
        #       ' -d \'{template}\''.format(template=_template(False)))
        deploy_url = self._url_maker(host, port)
        try:
            resp = requests.post(deploy_url, data=t, cert=CERTS, verify=False, timeout=7)
        except:
            self.status = DA_TASK_STATUS_K8S_NO_RESPONSE
        else:
            self.status_payload = self._k8s_filter(resp.content)
            self.status = DA_TASK_STATUS_READY

    @classmethod
    def _get_name(cls, status_payload):
        try:
            name = status_payload['items'][0]['metadata']['name']
        except KeyError:
            name = None
        return name

    @classmethod
    def _get_phase(cls, status_payload):
        try:
            phase = status_payload['items'][0]['status']['phase']
        except KeyError:
            phase = None
        return phase

    def update_status(self, host, port):
        status_payload = self.status_payload
        if not status_payload:
            self.status = DA_TASK_STATUS_K8S_NO_RESPONSE
        elif 'status' in status_payload and status_payload['status'] == 'fail':
            self.status = DA_TASK_STATUS_ERROR
        elif 'code' in status_payload or 'Code' in status_payload:  # TODO 'Code' is not a correct key
            name = self._get_name(status_payload)
            if not name:
                self.status = DA_TASK_STATUS_START_FAIL
                return

            # Fetch k8s status and save
            try:
                resp = requests.get(self._query_url_maker(host, port, name), cert=CERTS, headers=HEADERS, verify=False, timeout=7)
            except requests.Timeout:
                raise Exception('The k8s timeout exception.')
            self.updated_at = datetime.utcnow()
            self.status_payload = json.loads(resp.content)
            latest_status = self._get_phase(status_payload)
            if self.status != latest_status:
                self.status = self._status_filter(latest_status)
        else:
            raise Exception('Unknown, %s' % (json.dumps(status_payload)))


class EsTaskOtaInst(QueryTaskDeviceMixin, Base):
    __tablename__ = 'es_task_ota_inst'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    task_id = Column(ForeignKey(u'es_tasks.id'), nullable=False)
    device_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    solution_id = Column(ForeignKey(u'dcca_ass_solution_images.id'), nullable=False)
    status = Column(Integer)
    status_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))

    device = relationship(u'Host')
    solution = relationship(u'DccaAssSolutionImage')
    task = relationship(u'EsTask')

    def __init__(self, task, device, solution):
        self.task = task
        self.device = device
        self.solution = solution
        self.status = OTA_TASK_CODE_START
        self.status_payload = {}

    @classmethod
    def query_devices(cls, task):
        devices = set()
        instances = cls.query_inst(task)
        for inst in instances:
            devices.add(inst.device)
        return devices

    @classmethod
    def query_inst(cls):
        pass

    def update_status(self):
        pass


class Host(Base):
    __tablename__ = 'hosts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    last_report = Column(DateTime, index=True)
    updated_at = Column(DateTime)
    created_at = Column(DateTime, server_default=text("now()"))
    owner_id = Column(Integer)
    enabled = Column(Boolean, server_default=text("true"))
    certname = Column(String(255), index=True)
    dcca_model_id = Column(ForeignKey(u'dcca_models.id'))
    display_name = Column(String(32))

    users = relationship('DccaUser', secondary=u'dcca_ass_user_device')
    tags = relationship('DccaTag', secondary=u'dcca_ass_device_tag')


ENUM_ENGINE_TRAINING = 'training'
ENUM_ENGINE_INTERFERENCE = 'interference'


class EngineEnum(Enum):
    """
    The Type of Enum
    """
    training = 1
    interference = 2

    @classmethod
    def values(cls):
        return [cls.training, cls.interference]

    @classmethod
    def items(cls):
        return [ENUM_ENGINE_TRAINING, ENUM_ENGINE_INTERFERENCE]


t_dcca_ass_ai_model_engine = Table(
    'dcca_ass_ai_model_engine', metadata,
    Column('model_id', ForeignKey(u'dcca_ai_models.id'), primary_key=True, nullable=False),
    Column('engine_id', ForeignKey(u'dcca_ai_engines.id'), primary_key=True, nullable=False)
)


class DccaAIEngine(OutputMixin, Base):
    """
    The AI engines
    """
    __tablename__ = 'dcca_ai_engines'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v1mc()"))
    name = Column(String(32), nullable=False)
    category = Column(Enum(u'training', u'interference', name='engine'), nullable=False)
    owner_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    url = Column(String(256))

    owner = relationship('DccaUser')
    ai_models = relationship(
        'DccaAIModel',
        secondary=t_dcca_ass_ai_model_engine,
        back_populates='engines'
    )

    def __init__(self, name, category, is_public=False, description='', url=''):
        self.name = name
        self.category = category
        self.owner = ctx.current_user
        self.is_public = is_public
        self.description = description
        self.url = url

    @classmethod
    def get(cls, id):
        """
        Get by ID, no auth check
        """
        return cls._query_by_id(id)

    @classmethod
    def get_all(cls, ids):
        return session.query(cls).filter(cls.id.in_(ids)).all()

    @classmethod
    def _query_by_id(cls, id):
        try:
            return session.query(cls).filter(cls.id == id).one()
        except NoResultFound:
            return None

    @classmethod
    def query_by_id(cls, id):
        try:
            return session.query(cls).filter(and_(cls.id == id, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def query_all(cls):
        engines = session.query(cls).filter(
            or_(
                cls.is_public==True,
                and_(
                    cls.is_public==False,
                    cls.owner == ctx.current_user
                )
            )
        ).order_by(cls.category).order_by(desc(cls.updated_at)).all()
        return engines

    def is_valid_engine(self):
        if self.is_public is True or self.owner == ctx.current_user:
            return True
        else:
            return False


class DccaAIModel(OutputMixin, Base):
    __tablename__ = 'dcca_ai_models'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v1mc()"))
    name = Column(String(64), nullable=False, server_default=text("''::character varying"))
    owner_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    url = Column(Text, nullable=False, server_default=text("''::text"))
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    storage = Column(Text, nullable=False, server_default=text("''::text"))

    owner = relationship('DccaUser')
    engines = relationship(
        'DccaAIEngine',
        secondary=t_dcca_ass_ai_model_engine,
        back_populates='ai_models'
    )

    def __init__(self, name, url, is_public=False, description='', storage=''):
        self.name = name
        self.url = url
        self.owner = ctx.current_user
        self.is_public = is_public
        self.description = description
        self.storage = storage

    @classmethod
    def get(cls, id):
        try:
            return session.query(cls).filter(cls.id == id).one()
        except NoResultFound:
            return None

    @classmethod
    def query_by_id(cls, id):
        try:
            return session.query(cls).filter(and_(cls.id == id, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def query_by_name(cls, name):
        try:
            return session.query(cls).filter(and_(cls.name == name, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def query_bulk_startswith_name(cls, name, reversed=False):
        query_set = session.query(cls).filter(
                        and_(
                            cls.name == name,
                            cls.owner == ctx.current_user
                        )
                    )

        if reversed:
            query_set = query_set.order_by(desc(cls.name))

        query_set = query_set.order_by(desc(cls.updated_at))

        return query_set.all()

    @classmethod
    def query_all(cls, fnt=None, fni=None, filter_name=None, limit=20, offset=0, order_by=None):
        """
        fnt: training engine filter
        fni: interference engine filter
        """
        limit = 20 if limit is None else limit
        offset = 0 if offset is None else offset

        query_set = session.query(cls).filter(
            or_(
                cls.is_public == True,
                cls.owner == ctx.current_user
            )
        )

        if filter_name:
            query_set = query_set.filter(cls.name.like(filter_name + '%'))

        if fnt or fni:
            query_set = query_set.outerjoin(t_dcca_ass_ai_model_engine).filter(DccaAIModel.id==t_dcca_ass_ai_model_engine.c.model_id) \
                                .outerjoin(DccaAIEngine).filter(t_dcca_ass_ai_model_engine.c.engine_id==DccaAIEngine.id)
            if fni:
                query_set = query_set.filter(DccaAIEngine.name.like(fni + '%'))

            if fnt:
                query_set = query_set.filter(DccaAIEngine.name.like(fnt + '%'))

        if order_by:
            if order_by.startswith('-'):
                reverse = True
            else:
                reverse = False

            if order_by.startswith('+') or order_by.startswith('-'):
                order_by = order_by[1:]

            if order_by in cls.__table__.columns:
                if reverse:
                    query_set = query_set.order_by(desc(getattr(cls, order_by)))
                else:
                    query_set = query_set.order_by(getattr(cls, order_by))

        query_set = query_set.order_by(desc(cls.updated_at))

        total = query_set.count()
        query_set = query_set.limit(limit).offset(offset)
        return query_set.all(), total

    def is_engine_binded(self, engine_id):
        engines = self.engines
        for engine in engines:
            if engine.id == engine_id:
                return True
        return False

    def valid_training_engine(self, engine):
        if not engine:
            return False
        if not engine.is_valid_engine() or engine.category != ENUM_ENGINE_TRAINING:
            return False
        return True

    def is_training_engine_binded(self, engine):
        if not engine:
            return False
        for engine in self.engines:
            if engine.category == ENUM_ENGINE_TRAINING:
                return True
        return False

    def valid_interference_engines(self, engines):
        invalid_engines = []
        for engine in engines:
            if not engine.is_valid_engine() or engine.category != ENUM_ENGINE_INTERFERENCE:
                invalid_engines.append(engine)

        if invalid_engines:
            return False, invalid_engines
        else:
            return True, []

    def bind_training_engine(self, engine):
        for engine in self.engines:
            if engine.category == ENUM_ENGINE_TRAINING:
                self.engines.remove(engine)
                break
        self.engines.insert(0, engine)

    def reset_interference_engines(self, engines):
        new = []
        for engine in self.engines:
            if engine.category == ENUM_ENGINE_TRAINING:
                new.append(engine)
                break

        for engine in engines:
            if engine.category == ENUM_ENGINE_INTERFERENCE:
                new.append(engine)
        self.engines = new

    def bind_engine(self, engine):
        if engine not in self.engines:
            self.engines.append(engine)

    def engine_as_dict(self):
        data = {
            ENUM_ENGINE_TRAINING: {},
            ENUM_ENGINE_INTERFERENCE: []
        }

        for engine in self.engines:
            engine_dict = engine.as_dict(schema=ModelEngineSchema)
            if engine.category == ENUM_ENGINE_TRAINING:
                data[engine.category] = engine_dict
            elif engine.category == ENUM_ENGINE_INTERFERENCE:
                data[engine.category].append(engine_dict)
        return data


t_dcca_ass_user_authority = Table(
    'dcca_ass_user_authority', metadata,
    Column('user_id', ForeignKey(u'dcca_users.id'), primary_key=True, nullable=False),
    Column('auth_id', ForeignKey(u'dcca_authorities.id'), primary_key=True, nullable=False)
)


AUTH_CHANGE_ENGINE_PRIVACY = 'can_change_engine_privacy'
AUTH_CHANGE_AI_MODEL_PRIVACY = 'can_change_ai_model_privacy'
class DccaAuthority(Base):
    __tablename__ = 'dcca_authorities'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_authorities_id_seq'::regclass)"))
    name = Column(String(32), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    description = Column(Text, nullable=False, server_default=text("''::text"))

    users = relationship('DccaUser', secondary=u'dcca_ass_user_authority')

    @classmethod
    def can_do(cls, name):
        try:
            if ctx.current_user.admin \
                or session.query(cls).join(t_dcca_ass_user_authority, cls.id == t_dcca_ass_user_authority.c.auth_id).filter(
                        and_(
                            cls.name == name,
                            t_dcca_ass_user_authority.c.user_id == ctx.current_user.id
                        )
                    ).one():
                return True
        except NoResultFound:
            return False
        return False

    @classmethod
    def can_change_engine_privacy(cls):
        if cls.can_do(AUTH_CHANGE_ENGINE_PRIVACY):
            return True
        else:
            return False

    @classmethod
    def can_change_model_privacy(cls):
        if cls.can_do(AUTH_CHANGE_AI_MODEL_PRIVACY):
            return True
        else:
            return False


class DccaCustomer(Base):
    __tablename__ = 'dcca_customers'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    name = Column(String(32), nullable=False)
    owner_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    description = Column(Text, nullable=False, server_default=text("''::text"))

    owner = relationship(u'DccaUser')

