# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8

from datetime import datetime
import json
from collections import OrderedDict
from operator import and_

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, \
    Index, Integer, JSON, SmallInteger, String, Table, Text, UniqueConstraint, text, func, desc
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

from model.ischema import ResourceSchema, RoleSchema, FullResourceSchema


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
            if "default" in kwargs:
                return kwargs['default']
            else:
                raise
    return obj


class OutputMixin(object):
    RELATIONSHIPS_TO_DICT = False

    def __iter__(self):
        return list(self.to_dict().items())

    def as_dict(self, schema=None):
        if not schema:
            raise Exception('Schema cannot be empty.')

        instance = schema()

        res = OrderedDict()
        for attr, field in list(instance.fields.items()):
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
        for attr, column in list(self.__mapper__.c.items()):
            if attr not in list(whitelist.keys()):
                continue

            value = getattr(self, attr)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')

            res[attr] = value

        if rel:
            for attr, relation in list(self.__mapper__.relationships.items()):
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


class DccaAccessRecord(Base):
    __tablename__ = 'dcca_access_records'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_access_records_id_seq'::regclass)"))
    uid = Column(Integer)
    username = Column(String(255))
    is_admin = Column(Integer)
    auth_at = Column(DateTime, server_default=text("now()"))
    method_arn = Column(String(256))


class DccaAccountType(Base):
    __tablename__ = 'dcca_account_types'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_account_type_id_seq'::regclass)"))
    name = Column(String(16), nullable=False, unique=True)
    description = Column(String(32))
    is_external = Column(Boolean, nullable=False, server_default=text("true"))


class DccaAccount(OutputMixin, Base):
    __tablename__ = 'dcca_accounts'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_accounts_id_seq'::regclass)"))
    company_name = Column(String(32))
    telephone = Column(String(16))
    email = Column(String(32), nullable=False, unique=True)
    job_title = Column(String(32))
    account_type_id = Column(ForeignKey('dcca_account_types.id'))
    first_name = Column(String(16))
    last_name = Column(String(16))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    status = Column(Integer, nullable=False, server_default=text("0"))

    account_type = relationship('DccaAccountType')

    @classmethod
    def query_all(cls, limit=10, offset=0):
        query_set = session.query(cls)
        query_set = query_set.order_by(cls.status).order_by(desc(cls.created_at))
        size = query_set.count()

        query_set = query_set.limit(limit).offset(offset)
        return query_set.all(), size

    @classmethod
    def query_all_example(cls, filter_name, order_by_column, limit=10, offset=0, reverse=False):
        # TODO remove soon
        query_set = session.query(DccaRole)
        if filter_name:
            query_set = query_set.from_self().filter(DccaRole.name.like('{}%'.format(filter_name)))

        if order_by_column and order_by_column in RoleSchema.Meta.fields:
            _order_by_column = getattr(DccaRole, order_by_column)
        else:
            _order_by_column = DccaRole.updated_at

        if reverse:
            _order_by_column = desc(_order_by_column)

        query_set = query_set.from_self().order_by(_order_by_column)

        size = query_set.count()
        query_set = query_set.from_self().limit(limit).offset(offset)
        return query_set.all(), size


class DccaApiAccessRecord(Base):
    __tablename__ = 'dcca_api_access_records'
    __table_args__ = (
        Index('dcca_api_access_records_user_id_access_date_index', 'user_id', 'access_date'),
    )

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_api_access_records_id_seq'::regclass)"))
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    access_date = Column(Date)
    record = Column(JSON)

    user = relationship('DccaUser')


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


class DccaApplication(Base):
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


t_dcca_ass_app_tag = Table(
    'dcca_ass_app_tag', metadata,
    Column('application_id', ForeignKey('dcca_applications.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey('dcca_tags.id'), primary_key=True, nullable=False)
)

t_dcca_ass_device_tag = Table(
    'dcca_ass_device_tag', metadata,
    Column('device_id', ForeignKey('hosts.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey('dcca_tags.id'), primary_key=True, nullable=False)
)


class DccaAssDeviceTask(Base):
    __tablename__ = 'dcca_ass_device_task'

    device_id = Column(ForeignKey('hosts.id'), primary_key=True, nullable=False)
    task_id = Column(ForeignKey('edgescale_tasks.id'), primary_key=True, nullable=False)
    status_payload = Column(JSON)

    device = relationship('Host')
    task = relationship('EdgescaleTask')


class DccaAssHostModel(Base):
    __tablename__ = 'dcca_ass_host_model'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_ass_host_model_id_seq'::regclass)"))
    host_id = Column(ForeignKey('hosts.id'), nullable=False)
    model_id = Column(ForeignKey('dcca_models.id'), nullable=False)

    host = relationship('Host')
    model = relationship('DccaModel')


t_dcca_ass_model_service = Table(
    'dcca_ass_model_service', metadata,
    Column('model_id', ForeignKey('dcca_models.id'), primary_key=True, nullable=False),
    Column('service_id', ForeignKey('dcca_services.id'), primary_key=True, nullable=False)
)

t_dcca_ass_model_softapp = Table(
    'dcca_ass_model_softapp', metadata,
    Column('model_id', ForeignKey('dcca_models.id'), nullable=False),
    Column('softapp_id', ForeignKey('dcca_softapps.id'), nullable=False),
    Index('dcca_ass_model_softapp_model_id_softapp_id_uindex', 'model_id', 'softapp_id', unique=True)
)


class DccaAssModelSoftware(Base):
    __tablename__ = 'dcca_ass_model_software'

    model_id = Column(ForeignKey('dcca_models.id'), nullable=False)
    software_id = Column(ForeignKey('dcca_softwares.swid'), nullable=False)
    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_ass_model_software_id_seq'::regclass)"))

    model = relationship('DccaModel')
    software = relationship('DccaSoftware')


t_dcca_ass_role_perm = Table(
    'dcca_ass_role_perm', metadata,
    Column('role_id', ForeignKey('dcca_roles.id'), primary_key=True, nullable=False),
    Column('perm_id', ForeignKey('dcca_permissions.id'), primary_key=True, nullable=False)
)


class DccaAssSolutionImage(Base):
    __tablename__ = 'dcca_ass_solution_images'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_ass_solution_images_id_seq'::regclass)"))
    solution = Column(String(64), nullable=False)
    model_id = Column(ForeignKey('dcca_models.id'), nullable=False)
    image = Column(Text, nullable=False)
    version = Column(String(64), nullable=False)
    link = Column(Text, nullable=False)
    is_public = Column(Boolean, server_default=text("true"))
    in_s3 = Column(Boolean, server_default=text("true"))
    public_key = Column(Text)
    is_signed = Column(Boolean, server_default=text("false"))
    logical_delete_flag = Column(Boolean, server_default=text("false"))
    owner_id = Column(ForeignKey('dcca_users.id'))

    model = relationship('DccaModel', primaryjoin='DccaAssSolutionImage.model_id == DccaModel.id')
    owner = relationship('DccaUser')
    tags = relationship('DccaTag', secondary='dcca_ass_solution_tag')
    users = relationship('DccaUser', secondary='dcca_ass_user_solution')


t_dcca_ass_solution_tag = Table(
    'dcca_ass_solution_tag', metadata,
    Column('solution_id', ForeignKey('dcca_ass_solution_images.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey('dcca_tags.id'), primary_key=True, nullable=False)
)

t_dcca_ass_user_device = Table(
    'dcca_ass_user_device', metadata,
    Column('user_id', ForeignKey('dcca_users.id'), nullable=False),
    Column('device_id', ForeignKey('hosts.id'), nullable=False),
    UniqueConstraint('user_id', 'device_id')
)


class DccaAssUserRole(Base):
    __tablename__ = 'dcca_ass_user_role'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_ass_user_role_id_seq'::regclass)"))
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    role_id = Column(ForeignKey('dcca_roles.id'), nullable=False)

    role = relationship('DccaRole')
    user = relationship('DccaUser')

    @classmethod
    def remove(cls, user, role):
        session.query(DccaAssUserRole).filter(and_(DccaAssUserRole.user == user, DccaAssUserRole.role == role)).delete()


t_dcca_ass_user_solution = Table(
    'dcca_ass_user_solution', metadata,
    Column('user_id', ForeignKey('dcca_users.id'), primary_key=True, nullable=False),
    Column('solution_id', ForeignKey('dcca_ass_solution_images.id'), primary_key=True, nullable=False)
)

t_dcca_ass_user_task = Table(
    'dcca_ass_user_task', metadata,
    Column('user_id', ForeignKey('dcca_users.id'), primary_key=True, nullable=False),
    Column('task_id', ForeignKey('edgescale_tasks.id'), primary_key=True, nullable=False)
)

t_dcca_ass_user_vendor = Table(
    'dcca_ass_user_vendor', metadata,
    Column('user_id', ForeignKey('dcca_users.id'), primary_key=True, nullable=False),
    Column('vendor_id', ForeignKey('dcca_vendors.id'), primary_key=True, nullable=False)
)


class DccaCertificate(Base):
    __tablename__ = 'dcca_certificates'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_certificates_id_seq'::regclass)"))
    body = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)
    chain = Column(Text)
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False, unique=True)

    user = relationship('DccaUser')


class DccaCommonService(Base):
    __tablename__ = 'dcca_common_services'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    type = Column(String(32))
    name = Column(String(32))
    url = Column(String(512))
    port = Column(String(5))
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    access_token = Column(String(128))

    user = relationship('DccaUser')


class DccaContinent(Base):
    __tablename__ = 'dcca_continents'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_continents_id_seq'::regclass)"))
    name = Column(String(16), nullable=False)
    short_name = Column(String(2), nullable=False)


class DccaDeployRecored(Base):
    __tablename__ = 'dcca_deploy_recoreds'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_deploy_recoreds_id_seq'::regclass)"))
    event = Column(JSON)
    template = Column(JSON)
    raw_k8s_result = Column(JSON)
    parsed_k8s_result = Column(JSON)
    resource = Column(String(256))
    task_id = Column(ForeignKey('edgescale_tasks.id'))
    device_id = Column(ForeignKey('hosts.id'))

    device = relationship('Host')
    task = relationship('EdgescaleTask')


class DccaDeviceAttribute(Base):
    __tablename__ = 'dcca_device_attributes'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_device_attributes_id_seq'::regclass)"))
    name = Column(String(24), nullable=False)
    description = Column(String(256))


class DccaDeviceIp(Base):
    __tablename__ = 'dcca_device_ip'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_device_ip_id_seq'::regclass)"))
    ip = Column(String(256))
    country = Column(String(16))
    continent = Column(String(8))
    latitude = Column(Float(53))
    longitude = Column(Float(53))
    device_id = Column(ForeignKey('hosts.id'))
    disabled = Column(Boolean, server_default=text("false"))

    device = relationship('Host')


class DccaDeviceNic(Base):
    __tablename__ = 'dcca_device_nics'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_device_nics_id_seq'::regclass)"))
    ip = Column(String(16))
    device_id = Column(ForeignKey('hosts.id'), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))

    device = relationship('Host')


class DccaDevicePosition(Base):
    __tablename__ = 'dcca_device_position'

    id = Column(Integer, primary_key=True, unique=True)
    latitude = Column(Float(53))
    longitude = Column(Float(53))
    location_id = Column(ForeignKey('dcca_locations.id'))
    continent_id = Column(ForeignKey('dcca_continents.id'))
    ip_address = Column(INET)

    continent = relationship('DccaContinent')
    location = relationship('DccaLocation')


class DccaHardware(Base):
    __tablename__ = 'dcca_hardwares'

    hwid = Column(Integer, primary_key=True, unique=True,
                  server_default=text("nextval('dcca_hardwares_hwid_seq'::regclass)"))
    name = Column(String(20), server_default=text("NULL::character varying"))
    url = Column(String(1024))


class DccaLocation(Base):
    __tablename__ = 'dcca_locations'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_locations_id_seq'::regclass)"))
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
    owner_id = Column(ForeignKey('dcca_users.id'))
    default_solution_id = Column(ForeignKey('dcca_ass_solution_images.id'))

    default_solution = relationship('DccaAssSolutionImage',
                                    primaryjoin='DccaModel.default_solution_id == DccaAssSolutionImage.id')
    owner = relationship('DccaUser')
    softapps = relationship('DccaSoftapp', secondary='dcca_ass_model_softapp')
    services = relationship('DccaService', secondary='dcca_ass_model_service')


class DccaOtaStatu(Base):
    __tablename__ = 'dcca_ota_status'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_ota_status_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)


class DccaPermission(OutputMixin, Base):
    __tablename__ = 'dcca_permissions'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_permissions_id_seq'::regclass)"))
    name = Column(String(64), nullable=False, unique=True)
    resource_type = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))
    resource_id = Column(ForeignKey('dcca_resources.id'))
    is_only_admin_allowed = Column(Boolean, nullable=False, server_default=text("false"))

    resource = relationship('DccaResource', primaryjoin='DccaPermission.resource_id==DccaResource.id',
                            back_populates='permission')
    roles = relationship('DccaRole', secondary='dcca_ass_role_perm')

    def __init__(self, name, resource_type, resource):
        self.name = name
        self.resource_type = resource_type
        self.resource = resource

    @classmethod
    def get_by_id(cls, perm_id):
        try:
            return session.query(DccaPermission).filter(DccaPermission.id == perm_id).one()
        except NoResultFound:
            return None

    @classmethod
    def classified_by_type(cls, resources):
        results = OrderedDict()
        for res in resources:
            resource_type = res.resource_type
            if resource_type not in results:
                results[resource_type] = []
            results[resource_type].append(res.as_dict(schema=FullResourceSchema))

        return results

    @classmethod
    def query_all(cls):
        """
        Query all resources that classified by resource_type
        :return:
        """
        resources = session.query(DccaPermission).order_by(cls.resource_type).all()
        return cls.classified_by_type(resources)

    @classmethod
    def exists(cls, name):
        try:
            return session.query(DccaPermission).filter(DccaPermission.name == name).one()
        except NoResultFound:
            return None

    def remove(self):
        session.delete(self)
        session.query(DccaResource).filter(DccaResource.id == self.resource_id).delete()


class DccaProgres(Base):
    __tablename__ = 'dcca_progress'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_progress_id_seq'::regclass)"))
    device_id = Column(Integer, nullable=False)
    label = Column(String(64), nullable=False)
    progress = Column(SmallInteger, nullable=False)
    message = Column(String(256))
    terminated = Column(Boolean, nullable=False, server_default=text("false"))


class DccaResource(OutputMixin, Base):
    __tablename__ = 'dcca_resources'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_resources_id_seq'::regclass)"))
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
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    perms = relationship('DccaPermission', secondary='dcca_ass_role_perm')

    def __init__(self, name, description=None):
        self.name = name
        self.description = description

    def __repr__(self):
        return '{}: <{}>'.format(self.__class__.__name__, self.name)

    @classmethod
    def get_by_id(cls, _id):
        try:
            return session.query(DccaRole).filter(DccaRole.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def query_all(cls, filter_name, order_by_column,  limit=10, offset=0, reverse=False):
        query_set = session.query(DccaRole)
        if filter_name:
            query_set = query_set.from_self().filter(DccaRole.name.like('{}%'.format(filter_name)))

        if order_by_column and order_by_column in RoleSchema.Meta.fields:
            _order_by_column = getattr(DccaRole, order_by_column)
        else:
            _order_by_column = DccaRole.updated_at

        if reverse:
            _order_by_column = desc(_order_by_column)

        query_set = query_set.from_self().order_by(_order_by_column)

        size = query_set.count()
        query_set = query_set.from_self().limit(limit).offset(offset)
        return query_set.all(), size

    def data(self, resources=None):
        role = self.as_dict(schema=RoleSchema)
        if resources is not None:
            _permissions = resources
        else:
            _permissions = self.perms

        role['resources'] = DccaPermission.classified_by_type(_permissions)
        return role

    @classmethod
    def exists(cls, name):
        if session.query(func.count(DccaRole.id)).filter(DccaRole.name == name).scalar():
            return True
        else:
            return False

    def remove(self):
        t_dcca_ass_role_perm.delete(t_dcca_ass_role_perm.c.role_id == self.id)
        session.query(DccaAssUserRole).filter(DccaAssUserRole.role_id == self.id).delete()
        session.delete(self)

    def query_resources(self):
        resources = []
        for perm in self.perms:
            resources.append(perm.as_dict(schema=FullResourceSchema))
        return resources

    def add_resource(self, resource):
        if resource not in self.perms:
            self.perms.append(resource)

    def remove_resource(self, resource):
        if resource in self.perms:
            self.perms.remove(resource)


class DccaService(Base):
    __tablename__ = 'dcca_services'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_services_id_seq'::regclass)"))
    uid = Column(String(32), nullable=False, unique=True)
    name = Column(String(32))
    server_certificate_format = Column(Enum('pem', name='server_certificate_format'))
    server_certificate_key = Column(String(512))
    connection_url = Column(String(512))
    config = Column(String(1024))
    signing_certificate_format = Column(Enum('pem', name='signing_certificate_format'))
    signing_certificate_key = Column(String(512))
    protocal = Column(String(16), nullable=False)
    cipher_suite = Column(String(64), nullable=False)
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False)

    user = relationship('DccaUser')


class DccaSoftapp(Base):
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

    application = relationship('DccaApplication')
    mirror = relationship('DccaAppMirror')


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


class DccaTagType(Base):
    __tablename__ = 'dcca_tag_types'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_tag_types_id_seq'::regclass)"))
    name = Column(String(32), nullable=False)
    desc = Column(String(128))


class DccaTag(Base):
    __tablename__ = 'dcca_tags'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_tags_id_seq'::regclass)"))
    name = Column(String(16), nullable=False, unique=True)
    description = Column(String(64))


class DccaTaskStatu(Base):
    __tablename__ = 'dcca_task_status'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_task_status_id_seq'::regclass)"))
    name = Column(String(10), nullable=False)


class DccaTaskType(Base):
    __tablename__ = 'dcca_task_types'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_task_types_id_seq'::regclass)"))
    name = Column(String(20), nullable=False)


class DccaTask(Base):
    __tablename__ = 'dcca_tasks'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_tasks_id_seq'::regclass)"))
    device_id = Column(ForeignKey('hosts.id'), nullable=False)
    start_time = Column(DateTime, nullable=False, server_default=text("now()"))
    end_time = Column(DateTime)
    type_id = Column(ForeignKey('dcca_task_types.id'), nullable=False)
    status_id = Column(ForeignKey('dcca_task_status.id'), nullable=False)
    solution_id = Column(ForeignKey('dcca_ass_solution_images.id'), nullable=False)
    ota_status_id = Column(ForeignKey('dcca_ota_status.id'))

    device = relationship('Host')
    ota_status = relationship('DccaOtaStatu')
    solution = relationship('DccaAssSolutionImage')
    status = relationship('DccaTaskStatu')
    type = relationship('DccaTaskType')


class DccaUserLimitType(Base):
    __tablename__ = 'dcca_user_limit_type'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_user_limit_type_id_seq'::regclass)"))
    name = Column(String(32), nullable=False)
    desc = Column(String(64))
    default_max_limit = Column(Integer, nullable=False)
    default_max_sec = Column(Integer)
    is_per_time = Column(Boolean, nullable=False, server_default=text("false"))


class DccaUserLimit(Base):
    __tablename__ = 'dcca_user_limits'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_user_limits_id_seq'::regclass)"))
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False, index=True)
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
    account_type_id = Column(ForeignKey('dcca_account_types.id'), server_default=text("4"))
    image = Column(String(256))

    account_type = relationship('DccaAccountType')
    vendors = relationship('DccaVendor', secondary='dcca_ass_user_vendor')
    roles = relationship('DccaRole', secondary='dcca_ass_user_role')

    @classmethod
    def get_by_id(cls, id):
        try:
            return session.query(DccaUser).filter(DccaUser.id == id).one()
        except NoResultFound:
            return None

    def has_role(self, role):
        if role in self.roles:
            return True
        else:
            return False

    def revoke_role(self, role):
        DccaAssUserRole.remove(self, role)

    def role_perm(self):
        data = []
        for role in self.roles:
            perm_data = OrderedDict()
            perm_data['role_id'] = role.id
            perm_data['name'] = role.name
            perm_data['resources'] = []

            data.append(perm_data)
            for perm in role.perms:
                perm_data['resources'].append(perm.as_dict(schema=ResourceSchema))

        return data


class DccaVendor(Base):
    __tablename__ = 'dcca_vendors'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_vendor_id_seq'::regclass)"))
    name = Column(String(32), nullable=False, unique=True)
    is_public = Column(Boolean, nullable=False, server_default=text("true"))


class EdgescaleTask(Base):
    __tablename__ = 'edgescale_tasks'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('edgescale_tasks_id_seq'::regclass)"))
    type = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Integer)
    timestamp = Column(DateTime, server_default=text("now()"))
    logical_delete = Column(Boolean, nullable=False, server_default=text("false"))


class Host(Base):
    __tablename__ = 'hosts'

    id = Column(Integer, primary_key=True, server_default=text("nextval('hosts_id_seq'::regclass)"))
    name = Column(String(255), nullable=False, unique=True)
    last_compile = Column(DateTime)
    last_report = Column(DateTime, index=True)
    updated_at = Column(DateTime)
    created_at = Column(DateTime, server_default=text("now()"))
    root_pass = Column(String(255))
    architecture_id = Column(ForeignKey('architectures.id'), index=True)
    operatingsystem_id = Column(ForeignKey('operatingsystems.id'), index=True)
    environment_id = Column(ForeignKey('environments.id'), index=True)
    ptable_id = Column(ForeignKey('templates.id'))
    medium_id = Column(ForeignKey('media.id'), index=True)
    build = Column(Boolean, server_default=text("false"))
    comment = Column(Text)
    disk = Column(Text)
    installed_at = Column(DateTime, index=True)
    model_id = Column(ForeignKey('models.id'))
    hostgroup_id = Column(ForeignKey('hostgroups.id'), index=True)
    owner_id = Column(Integer)
    owner_type = Column(String(255))
    enabled = Column(Boolean, server_default=text("true"))
    puppet_ca_proxy_id = Column(ForeignKey('smart_proxies.id'))
    managed = Column(Boolean, nullable=False, server_default=text("false"))
    use_image = Column(Boolean)
    image_file = Column(String(128))
    uuid = Column(String(255))
    compute_resource_id = Column(ForeignKey('compute_resources.id'))
    puppet_proxy_id = Column(ForeignKey('smart_proxies.id'))
    certname = Column(String(255), index=True)
    image_id = Column(ForeignKey('images.id'))
    organization_id = Column(ForeignKey('taxonomies.id'))
    location_id = Column(ForeignKey('taxonomies.id'))
    type = Column(String(255), index=True)
    otp = Column(String(255))
    realm_id = Column(ForeignKey('realms.id'))
    compute_profile_id = Column(ForeignKey('compute_profiles.id'), index=True)
    provision_method = Column(String(255))
    grub_pass = Column(String(255), server_default=text("''::character varying"))
    global_status = Column(Integer, nullable=False, server_default=text("0"))
    lookup_value_matcher = Column(String(255))
    pxe_loader = Column(String(255))
    dcca_model_id = Column(ForeignKey('dcca_models.id'))
    display_name = Column(String(32))

    users = relationship('DccaUser', secondary='dcca_ass_user_device')
    tags = relationship('DccaTag', secondary='dcca_ass_device_tag')
