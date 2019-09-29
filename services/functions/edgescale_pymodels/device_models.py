# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
from sqlalchemy import JSON, Integer, text, String, Float, Boolean, DateTime, SmallInteger, exists, func, asc
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship

from edgescale_pymodels import constants
from edgescale_pymodels import solution_models
from edgescale_pymodels import tag_models
from edgescale_pymodels.base_model import *
from edgescale_pyutils.exception_utils import InvalidInputException


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

    @classmethod
    def get_all_model_id(cls, limit, offset):
        try:
            return session.query(DccaAssHostModel.model_id).limit(limit).offset(offset).all()
        except NoResultFound:
            return None

    @classmethod
    def get_model_deviceid(cls, _model_id):
        try:
            return session.query(DccaAssHostModel.host_id).outerjoin(Host, DccaAssHostModel.host_id == Host.id).filter(
                and_(DccaAssHostModel.model_id == _model_id, Host.owner_id == ctx.current_user.id)).all()

        except NoResultFound:
            return None
        # TODO
        # except Exception as e:
        #    return None

    @classmethod
    def has_devices(cls, _model_id):
        try:
            r = session.query(DccaAssHostModel.host_id).outerjoin(Host, DccaAssHostModel.host_id == Host.id).filter(
                and_(DccaAssHostModel.model_id == _model_id, Host.owner_id == ctx.current_user.id)).limit(1).one()

            if r and len(r) > 0:
                return True
            return False

        except NoResultFound:
            return None

    @classmethod
    def get_id(cls, _model_id):
        try:
            return session.query(DccaAssHostModel.id).filter(DccaAssHostModel.model_id == _model_id).one()
        except NoResultFound:
            return None


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

    @classmethod
    def query_by_location(cls, name):
        pass
        # location = DccaLocation.query_by_name(name)

    @classmethod
    def query_by_location_name(cls, location_id):
        try:
            return session.query(cls).filter(cls.location_id == location_id).all()
        except NoResultFound:
            return []


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

    @classmethod
    def query_by_name(cls, name):
        try:
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound:
            return None


class DccaOtaStatu(Base):
    __tablename__ = 'dcca_ota_status'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_ota_status_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)


class DccaProgres(Base):
    __tablename__ = 'dcca_progress'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_progress_id_seq'::regclass)"))
    device_id = Column(Integer, nullable=False)
    label = Column(String(64), nullable=False)
    progress = Column(SmallInteger, nullable=False)
    message = Column(String(256))
    terminated = Column(Boolean, nullable=False, server_default=text("false"))


class DccaDeviceGroup(QueryByIDMixin, QueryAllMixin, OutputMixin, Base):
    __tablename__ = 'dcca_device_groups'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    name = Column(String(16), nullable=False)
    desc = Column(String(32), nullable=False)
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"))
    is_public = Column(Boolean, default=False)
    model = Column(Boolean, default=False)
    customer_id = Column(UUID)

    owner = relationship('DccaUser')
    devices = relationship('Host', secondary='dcca_ass_device_group')

    def __init__(self, name, description, customer, is_public=False, model=False):
        self.name = name
        self.owner = ctx.current_user
        self.desc = description
        self.is_public = is_public
        self.model = model
        self.customer_id = customer

    @classmethod
    def get_by_id(cls, _id, uid):
        try:
            return session.query(cls).filter(or_(cls.owner_id == uid, cls.model.is_(True))).filter(
                DccaDeviceGroup.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def query_all_group_id(cls, uid):
        try:
            return session.query(cls.id).filter(cls.owner_id == uid).all()
        except NoResultFound:
            return None

    @classmethod
    def get_by_name(cls, name, uid):
        try:
            return session.query(DccaDeviceGroup).\
                filter(and_(DccaDeviceGroup.name == name, cls.model.is_(True))).first()
        except NoResultFound:
            return None

    @classmethod
    def get_model_groups(cls, limit, offset):
        try:
            return session.query(cls).filter(cls.model.is_(True)).all()
        except NoResultFound:
            return None

    @classmethod
    def get_model_name(cls):
        try:
            return session.query(cls.name).filter(cls.model.is_(True)).all()
        except NoResultFound:
            return None

    @classmethod
    def has_name(cls, name, get_name):
        if name in get_name:
            return True
        else:
            return False

    @classmethod
    def remove_by_name(cls, name):
        group = cls.get_by_name(name, ctx.current_user)
        if group:
            if group.category == constants.GROUP_CATEGORY_DEVICE:
                group.remove()

    @classmethod
    def exists(cls, name, user):
        if session.query(
                exists().where(and_(DccaDeviceGroup.name == name, DccaDeviceGroup.owner_id == user.id))).scalar():
            return True
        else:
            return False

    @classmethod
    def is_name_taken(cls, name, user):
        if cls.exists(name, user):
            raise InvalidInputException('The name "{}" has been taken'.format(name))

    def remove(self):
        t_dcca_ass_device_group.delete(t_dcca_ass_device_group.c.group_id == self.id)
        session.delete(self)

    def make_statistics(self):
        """
        1. First make statistics, then cache in memcached. Changed regularly
        2. Regularly cached
        :return:
        """
        devices = session.query(t_dcca_ass_device_group)

    def query_bind_devices(self, limit, offset):
        devices = session.query(t_dcca_ass_device_group) \
            .filter(t_dcca_ass_device_group.c.group_id == self.id).all()
        return devices

    @classmethod
    def query_bind_model_devices(cls, group_id, uid):
        devices = session.query(t_dcca_ass_device_group.c.device_id) \
            .filter(t_dcca_ass_device_group.c.group_id == group_id).all()
        return devices

    @classmethod
    def query_group_devices(cls, group_id):
        devices = session.query(t_dcca_ass_device_group.c.device_id) \
            .filter(t_dcca_ass_device_group.c.group_id == group_id).all()
        return devices

    def bind_device(self, device_ids=[]):
        pass


class Host(QueryByIDMixin, GetterByNameMixin, GetterMethodMixin, QueryInIdMixin,
           QueryAllMixin, OutputMixin, Base):
    __tablename__ = 'hosts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    last_report = Column(DateTime, index=True)
    updated_at = Column(DateTime)
    created_at = Column(DateTime, server_default=text("now()"))
    owner_id = Column(ForeignKey('dcca_users.id'))
    certname = Column(String(255), index=True)
    dcca_model_id = Column(ForeignKey('dcca_models.id'))
    lifecycle = Column(SmallInteger)
    display_name = Column(String(32))
    oem_uid = Column(Integer, index=True)
    customer_id = Column(ForeignKey('dcca_customers.id'))
    solution_id = Column(ForeignKey('dcca_ass_solution_images.id'))

    model = relationship('DccaModel')
    customer = relationship('DccaCustomer')
    owner = relationship('DccaUser', primaryjoin='Host.owner_id==DccaUser.id')
    tags = relationship('DccaTag', secondary='dcca_ass_device_tag')
    groups = relationship('DccaDeviceGroup', secondary='dcca_ass_device_group')

    def __init__(self, name, dcca_model_id, owner, customer=None):
        self.name = name
        self.owner = owner
        if owner.account_type_id == 2:
            self.oem_uid = owner.id
        else:
            self.oem_uid = 0

        self.customer = customer
        self.dcca_model_id = dcca_model_id

    @classmethod
    def valid_name(cls, name):
        if not name:
            return False, ''
        elif len(name) > 64:
            return False, 'The name length cannot bigger than 64.'
        elif len(name) < 6:
            return False, 'The name length cannot smaller that 6'

        return True, ''

    @classmethod
    def _dst_key(cls, device_name):
        """
        The dst: device status
        """

        return 'st:%s' % device_name

    @classmethod
    def _cdc_key(cls):
        """
        The cdc: create device counter
        """
        return 'j2:{0}:cdc'.format(ctx.current_user.id)

    def status(self):
        status_key = self._dst_key(self.name)
        _status = self.redis_client.hgetall(status_key)
        return _status

    @classmethod
    def size(cls):
        qs = session.query(cls).filter(cls.owner == ctx.current_user) \
            .statement.with_only_columns([func.count()]).order_by(None)
        size = session.execute(qs).scalar()

        cls.redis_client.set(cls._cdc_key(), size)
        return size

    @classmethod
    def query_by_location(cls, name, limit=5000, offset=0):
        location = DccaLocation.query_by_name(name)

        query_set = session.query(cls).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.id == DccaDevicePosition.id,
                DccaDevicePosition.location_id == location.id
            )
        )
        return query_set.limit(limit).offset(offset).all()

    @classmethod
    def query_by_platform(cls, platform, limit=5000, offset=0):
        query_set = session.query(cls).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.dcca_model_id == solution_models.DccaModel.id,
                solution_models.DccaModel.platform == platform
            )
        )

        return query_set.limit(limit).offset(offset).all()

    @classmethod
    def query_by_solution(cls, solution_id, limit=5000, offset=0):
        query_set = session.query(cls).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.dcca_model_id == solution_models.DccaModel.id,
                solution_models.DccaModel.id == solution_models.DccaAssSolutionImage.model_id,
                solution_models.DccaAssSolutionImage.id == solution_id
            )
        )
        return query_set.limit(limit).offset(offset).all()

    def bind_customer(self, customer):
        self.customer = customer

    @classmethod
    def group_by_customer(cls, customer, limit, offset):
        query_set = session.query(cls).filter(cls.customer == customer)
        total = query_set.count()
        devices = query_set.limit(limit).offset(offset).all()
        return devices, total

    @classmethod
    def batch_bind_customer(cls, device_ids, customer):
        if not device_ids:
            return []
        devices = session.query(cls).filter(and_(cls.id.in_(device_ids), cls.owner == ctx.current_user)).all()
        for d in devices:
            d.customer = customer
        return devices

    @classmethod
    def query_by_name(cls, name):
        try:
            return session.query(cls).filter(
                and_(cls.name == name,
                     cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_id(cls, _id):
        try:
            return session.query(Host).filter(and_(Host.id == _id, or_(cls.owner_id == ctx.current_user.id,
                                                                       cls.oem_uid == ctx.current_user.id))).one()
        except NoResultFound:
            return None

    @classmethod
    def query_in(cls, ids):
        return session.query(cls).filter(
            and_(cls.id.in_(ids), or_(cls.owner_id == ctx.current_user.id, cls.oem_uid == ctx.current_user.id))).all()

    @classmethod
    def get_id(cls, _id):
        try:
            return session.query(Host).filter(Host.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def get_model_id(cls, _id):
        try:
            return session.query(Host.dcca_model_id).filter(Host.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def model_has_device(cls, _id):
        try:
            return session.query(cls).filter(and_(cls.dcca_model_id == _id,
                                                  cls.owner_id == ctx.current_user.id)).limit(1).one()
        except NoResultFound:
            return None

    @classmethod
    def get_model_device(cls, _id, limit, offset):
        try:
            return session.query(Host).filter(Host.dcca_model_id == _id).all()
        except NoResultFound:
            return None

    @classmethod
    def get_all_device_id(cls):
        try:
            return session.query(Host.id).all()
        except NoResultFound:
            return None

    def has_group(self, group):
        if group in self.groups:
            return True
        else:
            return False

    @classmethod
    def query_all_devices_by_filter(cls, uid=None, display_name=None, location=None, platform=None, device_tag=None,
                                    model_id=None, order_type=None, order_by=None, limit=None, offset=0):

        query_all = session.query(cls, solution_models.DccaModel)\
            .join(solution_models.DccaModel, solution_models.DccaModel.id == cls.dcca_model_id)\
            .filter(
            or_(cls.owner_id == uid,
                cls.oem_uid == uid
                )
        )

        if display_name:
            query_all = query_all.filter(cls.display_name.like('%{}%'.format(display_name)))

        if location:
            d_location = DccaLocation.query_by_name(location)
            if not d_location:
                return 0, []

            positions = DccaDevicePosition.query_by_location_name(d_location.id)
            if not positions:
                return 0, []

            position_ids = [d.id for d in positions]
            query_all = query_all.filter(cls.id.in_(position_ids))

        if platform:
            d_models = solution_models.DccaModel.query_by_platform(platform)
            if not d_models:
                return 0, []
            model_ids = [m.id for m in d_models]

            query_all = query_all.filter(cls.dcca_model_id.in_(model_ids))
        if model_id:
            query_all = query_all.filter(cls.dcca_model_id == model_id)

        if device_tag:
            tags = tag_models.DccaTag.query_by_tag_name(device_tag)
            if not tags:
                return 0, []
            tag_ids = [t.id for t in tags]

            d__devices = DccaAssDeviceTag.query_by_tag_ids(tag_ids)
            if not d__devices:
                return 0, []
            device_ids = [d.device_id for d in d__devices]

            query_all = query_all.filter(cls.id.in_(device_ids))

        item = getattr(cls, order_by, cls.created_at)

        if order_type == 'asc':
            query_all = query_all.order_by(asc(item))
        else:
            query_all = query_all.order_by(desc(item))

        total = query_all.count()
        devices = query_all.offset(offset).limit(limit).all()

        return total, devices

    @classmethod
    def query_ota_statistics(cls):
        results = session.query(Host).outerjoin(
            solution_models.DccaAssSolutionImage, solution_models.DccaAssSolutionImage.id == Host.solution_id
        ).filter(
            and_(
                Host.owner_id == ctx.current_user.id,
                Host.solution_id.isnot(None)
            )
        ).all()

        return results

    @classmethod
    def query_ota_devices(cls, solution_id=None, limit=20, offset=0):
        query_set = session.query(cls).filter(
            and_(
                cls.owner_id == ctx.current_user.id,
                cls.solution_id.isnot(None)
            )
        )

        if solution_id:
            query_set = query_set.filter(cls.solution_id == solution_id)

        query_set = query_set.order_by(desc(cls.id))
        total = query_set.count()
        devices = query_set.offset(offset).limit(limit).all()

        return total, devices


class DccaAssDeviceTag(Base):
    __tablename__ = 'dcca_ass_device_tag'
    device_id = Column('device_id', ForeignKey(u'hosts.id'), primary_key=True, nullable=False)
    tag_id = Column('tag_id', ForeignKey(u'dcca_tags.id'), primary_key=True, nullable=False)

    @classmethod
    def query_by_tag_ids(cls, tag_ids):
        if not tag_ids:
            return []
        try:
            return session.query(cls).filter(cls.tag_id.in_(tag_ids)).all()
        except NoResultFound:
            return []


class ScaleSubdevReg(Base):
    __tablename__ = 'scale_subdev_reg'

    id = Column(Integer, primary_key=True, server_default=text("nextval('scale_subdev_reg_id_seq'::regclass)"))
    model_id = Column(String(64), nullable=False, index=True)
    devid = Column(String(64), nullable=False, index=True)
    hostid = Column(Integer, nullable=False, index=True)
    owner_id = Column(Integer, server_default=text("0"))

    @classmethod
    def query_by_hosts_ids(cls, ids):
        if not ids:
            return []
        try:
            return session.query(cls).filter(cls.hostid.in_(ids)).all()
        except NoResultFound:
            return []
