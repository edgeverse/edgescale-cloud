# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
from sqlalchemy import Integer, text, Text, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship

from edgescale_pymodels import user_models
from edgescale_pymodels.base_model import *
from edgescale_pymodels.ischema import FullResourceSchema, RoleSchema


class DccaCertificate(Base):
    __tablename__ = 'dcca_certificates'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_certificates_id_seq'::regclass)"))
    body = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)
    chain = Column(Text)
    user_id = Column(ForeignKey('dcca_users.id'), nullable=False, unique=True)

    user = relationship('DccaUser')


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
    def query_all(cls, filter_name, order_by_column, limit=10, offset=0, reverse=False):
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
        session.query(user_models.DccaAssUserRole).filter(user_models.DccaAssUserRole.role_id == self.id).delete()
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
