# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
from datetime import datetime
from collections import OrderedDict
import json

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Column, Enum, ForeignKey, Index, Table, UniqueConstraint, and_, or_, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

from edgescale_pyutils.model_utils import ctx


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
            if 'default' in kwargs:
                return kwargs['default']
            else:
                raise
    return obj


class QueryInIdMixin(object):
    @classmethod
    def query_in(cls, ids):
        return session.query(cls).filter(and_(cls.id.in_(ids), cls.owner == ctx.current_user)).all()


class OutputMixin(object):
    RELATIONSHIPS_TO_DICT = False

    def __iter__(self):
        return iter(self.to_dict().items())

    def as_dict(self, schema=None):
        if not schema:
            raise Exception('Schema cannot be empty.')

        instance = schema()

        res = OrderedDict()
        for attr, field in instance.fields.items():
            attr_name = field.metadata.get('attr')
            if not attr_name:
                attr_name = attr

            attr_value = nested_getattr(self, attr_name)

            filter_func = field.metadata.get('func')
            if filter_func:
                attr_value = filter_func(attr_value)

            rename = field.metadata.get('rename')
            if rename:
                res[rename] = attr_value
            else:
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


class GetterMethodMixin(object):
    @classmethod
    def get(cls, _id):
        try:
            return session.query(cls).filter(cls.id == _id).one()
        except NoResultFound:
            return None


class GetterByNameMixin(object):
    @classmethod
    def get_by_name(cls, name):
        try:
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound:
            return None


class QueryByIDMixin(object):
    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).filter(and_(cls.id == _id, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None


class QueryAllNoOwnerMixin(object):
    @classmethod
    def query_all(cls, limit=2000, offset=0):
        return session.query(cls).limit(limit).offset(offset).all()


class QueryAllMixin(object):
    @classmethod
    def query_all(cls, schema, order_column, uid, filter_name=None, limit=20, offset=0):
        """
        The mixin helps to query those have owner_id in table or do not need owner.
        :param order_column:
        :param filter_name:
        :param limit:
        :param offset:
        :return:
        """

        if filter_name:
            query_set = session.query(cls).filter()
            query_set = query_set.from_self().filter(cls.name.like('%{}%'.format(filter_name)))
            query_set = query_set.from_self().filter(or_(cls.owner_id == uid, cls.model.is_(True)))
        else:
            query_set = session.query(cls).filter(cls.model.is_(False))
            query_set = query_set.from_self().filter(cls.owner_id == uid)

        # if ctx.current_user:

        if order_column:
            reverse = False
            if order_column.startswith('-'):
                reverse = True
                order_column = order_column[1:]
            elif order_column.startswith('+'):
                order_column = order_column[1:]

            if order_column not in schema.Meta.fields:
                pass  # Not orderable for security
            else:
                _order_column = getattr(cls, order_column)

                if reverse:
                    _order_by_column = desc(_order_column)
                else:
                    _order_by_column = _order_column

                query_set = query_set.from_self().order_by(_order_by_column)
        elif hasattr(cls, 'updated_at'):
            _order_column = getattr(cls, 'updated_at')
            _order_by_column = desc(_order_column)
            query_set = query_set.from_self().order_by(_order_by_column)

        size = query_set.count()
        query_set = query_set.from_self().limit(limit).offset(offset)
        return query_set.all(), size


class RawEnum:
    device = 1
    user = 2


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


t_dcca_ass_app_tag = Table(
    'dcca_ass_app_tag', metadata,
    Column('application_id', ForeignKey('dcca_applications.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey('dcca_tags.id'), primary_key=True, nullable=False)
)

t_dcca_ass_device_group = Table(
    'dcca_ass_device_group', metadata,
    Column('device_id', ForeignKey('hosts.id'), primary_key=True, nullable=False),
    Column('group_id', ForeignKey('dcca_device_groups.id'), primary_key=True, nullable=False)
)

t_dcca_ass_dgroup_device = Table(
    'dcca_ass_dgroup_device', metadata,
    Column('device_id', ForeignKey('hosts.id'), primary_key=True, nullable=False),
    Column('group_id', ForeignKey('dcca_groups.id'), primary_key=True, nullable=False)
)

# t_dcca_ass_device_tag = Table(
#     'dcca_ass_device_tag', metadata,
#     Column('device_id', ForeignKey('hosts.id'), primary_key=True, nullable=False),
#     Column('tag_id', ForeignKey('dcca_tags.id'), primary_key=True, nullable=False)
# )

t_dcca_ass_role_perm = Table(
    'dcca_ass_role_perm', metadata,
    Column('role_id', ForeignKey('dcca_roles.id'), primary_key=True, nullable=False),
    Column('perm_id', ForeignKey('dcca_permissions.id'), primary_key=True, nullable=False)
)

t_dcca_ass_solution_tag = Table(
    'dcca_ass_solution_tag', metadata,
    Column('solution_id', ForeignKey('dcca_ass_solution_images.id'), primary_key=True, nullable=False),
    Column('tag_id', ForeignKey('dcca_tags.id'), primary_key=True, nullable=False)
)

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

t_dcca_ass_ai_model_engine = Table(
    'dcca_ass_ai_model_engine', metadata,
    Column('model_id', ForeignKey('dcca_ai_models.id'), primary_key=True, nullable=False),
    Column('engine_id', ForeignKey('dcca_ai_engines.id'), primary_key=True, nullable=False)
)

t_dcca_ass_template_device = Table(
    'dcca_ass_template_device', metadata,
    Column('template_id', ForeignKey('dcca_task_templates.id'), primary_key=True, nullable=False),
    Column('device_id', ForeignKey('hosts.id'), primary_key=True, nullable=False)
)

t_dcca_ass_user_authority = Table(
    'dcca_ass_user_authority', metadata,
    Column('user_id', ForeignKey('dcca_users.id'), primary_key=True, nullable=False),
    Column('auth_id', ForeignKey('dcca_authorities.id'), primary_key=True, nullable=False)
)

t_dcca_ass_user_device = Table(
    'dcca_ass_user_device', metadata,
    Column('user_id', ForeignKey('dcca_users.id'), nullable=False),
    Column('device_id', ForeignKey('hosts.id'), nullable=False),
    UniqueConstraint('user_id', 'device_id')
)

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
