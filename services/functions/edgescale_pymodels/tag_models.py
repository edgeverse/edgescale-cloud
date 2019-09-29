# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
from sqlalchemy import Integer, text, String

from edgescale_pymodels.base_model import *


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

    @classmethod
    def query_in_name(cls, names):
        return session.query(cls).filter(cls.name.in_(names)).all()

    @classmethod
    def query_by_tag_name(cls, name):
        try:
            return session.query(cls).filter(cls.name == name).all()
        except NoResultFound:
            return None

