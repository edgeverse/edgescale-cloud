# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
from sqlalchemy import Integer, text, String, DateTime, Date, JSON, Boolean, Text, asc
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.orm import relationship

from edgescale_pymodels import role_models
from edgescale_pymodels.base_model import *
from edgescale_pymodels.ischema import RoleSchema, ResourceSchema
from edgescale_pyutils.exception_utils import DCCAException


class DccaAccessRecord(Base):
    __tablename__ = 'dcca_access_records'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_access_records_id_seq'::regclass)"))
    uid = Column(Integer)
    username = Column(String(255))
    is_admin = Column(Integer)
    auth_at = Column(DateTime, server_default=text("now()"))
    method_arn = Column(String(256))


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
    def query_all(cls, filter_text, filter_type, filter_status, order_by='desc',
                  order_type='created_at', limit=10, offset=0):
        query_set = session.query(cls).order_by(cls.status)
        if filter_text:
            query_set = query_set.filter(DccaAccount.first_name.like('%{}%'.format(filter_text)))

        if filter_type:
            query_set = query_set.filter(DccaAccount.account_type_id == filter_type)

        if filter_status:
            query_set = query_set.filter(DccaAccount.status == filter_status)

        item = getattr(cls, order_by, cls.id)
        if order_type == 'asc':
            query_set = query_set.order_by(asc(item))
        else:
            query_set = query_set.order_by(desc(item))
        size = query_set.count()

        query_set = query_set.limit(limit).offset(offset)
        return query_set.all(), size

    @classmethod
    def query_all_example(cls, filter_name, order_by_column, limit=10, offset=0, reverse=False):
        # TODO remove soon
        query_set = session.query(role_models.DccaRole)
        if filter_name:
            query_set = query_set.from_self().filter(role_models.DccaRole.name.like('{}%'.format(filter_name)))

        if order_by_column and order_by_column in RoleSchema.Meta.fields:
            _order_by_column = getattr(role_models.DccaRole, order_by_column)
        else:
            _order_by_column = role_models.DccaRole.updated_at

        if reverse:
            _order_by_column = desc(_order_by_column)

        query_set = query_set.from_self().order_by(_order_by_column)

        size = query_set.count()
        query_set = query_set.from_self().limit(limit).offset(offset)
        return query_set.all(), size


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

    def __init__(self, user, limit_type_id, max_limit, max_sec):
        self.user = user
        self.limit_type_id = limit_type_id
        self.max_limit = max_limit
        self.max_sec = max_sec

    @classmethod
    def query_limits(cls, user):
        limits = session.query(cls).filter(cls.user == user).all()
        return [l.limit_type_id for l in limits]

    @classmethod
    def make(cls, user):
        limit_ids = cls.query_limits(user)
        limit_types = session.query(DccaUserLimitType).all()
        for lt in limit_types:
            if lt.id not in limit_ids:
                user_limit = cls(user, limit_type_id=lt.id, max_limit=lt.default_max_limit, max_sec=lt.default_max_sec)
                session.add(user_limit)

    @classmethod
    def get_limit_value(cls, type_id):
        try:
            return session.query(cls).filter(
                and_(cls.user_id == ctx.current_user.id,
                     cls.limit_type_id == type_id
                     )).one().max_limit
        except NoResultFound:
            return 0
        except DCCAException:
            return 0


class DccaUser(GetterMethodMixin, OutputMixin, Base):
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
    oem_id = Column(BIT(32, True))

    account_type = relationship('DccaAccountType')
    vendors = relationship('DccaVendor', secondary='dcca_ass_user_vendor')
    roles = relationship('DccaRole', secondary='dcca_ass_user_role')

    @classmethod
    def get_by_id(cls, _id):
        try:
            return session.query(DccaUser).filter(DccaUser.id == _id).one()
        except NoResultFound:
            return None
        except Exception as e:
            raise Exception(str(e))

    @classmethod
    def query_user_devices(cls, user_id):
        device_ids = session.query(t_dcca_ass_user_device.c.device_id) \
            .filter(t_dcca_ass_user_device.c.user_id == user_id).all()
        return device_ids

    @classmethod
    def get_all_users(cls):
        try:
            return session.query(cls.id).all()
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


class DccaVendor(OutputMixin, Base):
    __tablename__ = 'dcca_vendors'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('dcca_vendor_id_seq'::regclass)"))
    name = Column(String(32), nullable=False, unique=True)
    is_public = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))

    def __init__(self, name, is_public):
        self.name = name
        self.is_public = is_public

    @classmethod
    def query_all(cls, limit=20, offset=0, filter_name=None, order_by=None, order_type=None):
        limit = 20 if limit is None else limit
        offset = 0 if offset is None else offset

        query_set = session.query(cls)

        if filter_name:
            query_set = query_set.filter(cls.name.like('%' + filter_name + '%'))

        if order_by:
            if order_type == 'desc':
                query_set = query_set.order_by(nested_getattr(cls, order_by).desc())
            else:
                query_set = query_set.order_by(nested_getattr(cls, order_by).asc())

        total = query_set.count()
        vendors = query_set.limit(limit).offset(offset).all()
        return vendors, total

    @classmethod
    def query_one(cls, _id):
        query_set = session.query(cls).filter(cls.id == _id)

        vendor = query_set.one()
        return vendor

    @classmethod
    def create_one(cls, new_obj):
        item = session.query(cls).filter(cls.name == new_obj.name).first()

        if not item:
            session.add(new_obj)
            session.commit()
            status = {"status": "success", "message": "create vendor successfully"}
        else:
            status = {"status": "fail", "message": "name has already exist"}

        return status

    @classmethod
    def delete_one(cls, _id):
        item = session.query(cls).filter(cls.id == _id).first()

        if not item:
            status = {"status": "fail", "message": "vendor is not exist"}
        else:
            session.delete(item)
            session.commit()
            status = {"status": "success", "message": "remove vendor successfully"}

        return status

    @classmethod
    def update_one(cls, _id, name):
        item = session.query(cls).filter(cls.id == _id).first()
        item_name = session.query(cls).filter(cls.name == name).first()

        if not item:
            return {"status": "fail", "message": "vendor is not exist"}

        if not item_name:
            item.name = name
            item.updated_at = datetime.now()
            session.commit()
            status = {"status": "success", "message": "update vendor successfully"}
        else:
            status = {"status": "fail", "message": "name has already exist"}

        return status


AUTH_CHANGE_ENGINE_PRIVACY = 'can_change_engine_privacy'
AUTH_CHANGE_AI_MODEL_PRIVACY = 'can_change_ai_model_privacy'


class DccaAuthority(Base):
    __tablename__ = 'dcca_authorities'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_authorities_id_seq'::regclass)"))
    name = Column(String(32), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    description = Column(Text, nullable=False, server_default=text("''::text"))

    users = relationship('DccaUser', secondary='dcca_ass_user_authority')

    @classmethod
    def can_do(cls, name):
        try:
            if ctx.current_user.admin \
                    or session.query(cls).join(t_dcca_ass_user_authority,
                                               cls.id == t_dcca_ass_user_authority.c.auth_id).\
                    filter(and_(cls.name == name,
                                t_dcca_ass_user_authority.c.user_id == ctx.current_user.id)).\
                    one():
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


class DccaCustomer(OutputMixin, GetterMethodMixin, QueryByIDMixin, Base):
    __tablename__ = 'dcca_customers'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    name = Column(String(32), nullable=False)
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    description = Column(Text, nullable=False, server_default=text("''::text"))

    owner = relationship('DccaUser')

    def __init__(self, name, description=''):
        self.name = name
        self.description = description
        self.owner = ctx.current_user

    @classmethod
    def query_all(cls, filter_name, limit, offset):
        if filter_name:
            query_set = session.query(cls).filter(
                and_(
                    cls.is_active.is_(True),
                    cls.owner == ctx.current_user,
                    cls.name.like('%' + filter_name + '%')
                )
            ).order_by(cls.updated_at.desc())
        else:
            query_set = session.query(cls).filter(
                and_(
                    cls.is_active.is_(True),
                    cls.owner == ctx.current_user
                )).order_by(cls.updated_at.desc())

        total = query_set.count()
        customers = query_set.limit(limit).offset(offset).all()
        return customers, total

    @classmethod
    def batch_query(cls, ids):
        return session.query(cls).filter(and_(cls.id.in_(ids), cls.owner == ctx.current_user)).all()

    @classmethod
    def get_by_id(cls, _id):
        try:
            return session.query(cls).filter(and_(cls.id == _id, cls.owner_id == ctx.current_user.id)).one()
        except NoResultFound:
            return None
