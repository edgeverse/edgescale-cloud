# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
import boto3
from sqlalchemy import Integer, String, Text, text, Boolean, JSON, DateTime, func, literal, distinct, SmallInteger, asc
from sqlalchemy.orm import relationship

from edgescale_pymodels.constants import LIMIT_TYPE_ID_CREATE_SOLUTION
from edgescale_pymodels import user_models
from edgescale_pymodels import task_models
from edgescale_pymodels import device_models
from edgescale_pymodels.base_model import *
from edgescale_pymodels.ischema import ModelEngineSchema
from edgescale_pyutils.exception_utils import DCCAException


class DccaAssSolutionImage(GetterMethodMixin, Base):
    __tablename__ = 'dcca_ass_solution_images'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_ass_solution_images_id_seq'::regclass)"))
    solution = Column(String(64), nullable=False)
    model_id = Column(ForeignKey('dcca_models.id'), nullable=False)
    image = Column(Text, nullable=False)
    version = Column(String(64), nullable=False)
    link = Column(Text, nullable=False)
    is_public = Column(Boolean, nullable=False, server_default=text("false"))
    in_s3 = Column(Boolean, server_default=text("true"))
    public_key = Column(Text)
    is_signed = Column(Boolean, server_default=text("false"))
    logical_delete_flag = Column(Boolean, server_default=text("false"))
    owner_id = Column(ForeignKey('dcca_users.id'))
    have_installer = Column(Boolean, nullable=False, server_default=text("false"))

    model = relationship('DccaModel', primaryjoin='DccaAssSolutionImage.model_id == DccaModel.id')
    owner = relationship('DccaUser')
    tags = relationship('DccaTag', secondary='dcca_ass_solution_tag')
    users = relationship('DccaUser', secondary='dcca_ass_user_solution')

    def __init__(self, name, model_id, image, version, url, owner_id, in_s3=False,
                 is_signed=False, has_installer=False):
        self.solution = name
        self.model_id = model_id
        self.image = image
        self.version = version
        self.link = url
        self.owner_id = owner_id
        self.in_s3 = in_s3
        self.is_signed = is_signed
        self.have_installer = has_installer

    @classmethod
    def is_solution_owner(cls, sid):
        count = session.query(func.count(cls.id)).filter(
            and_(
                cls.owner_id == ctx.current_user.id,
                cls.id == sid
            )
        ).scalar()

        if count:
            return True
        else:
            return False

    @classmethod
    def check_solution_limit(cls):
        solution_size = session.query(func.count(cls.id)).filter(
            and_(cls.owner_id == ctx.current_user.id,
                 cls.logical_delete_flag.is_(False))
        ).scalar()

        solution_limit = user_models.DccaUserLimit.get_limit_value(LIMIT_TYPE_ID_CREATE_SOLUTION)

        if solution_size >= solution_limit:
            return True, solution_limit
        else:
            return False, solution_limit

    @classmethod
    def check_solution_name(cls, name, model_id):
        res = session.query(literal(True)).filter(
                    session.query(cls.id).filter(
                        and_(
                            cls.solution == name,
                            cls.model_id == model_id
                        )
                    ).exists()
        ).scalar()

        if res:
            return True
        else:
            return False

    @classmethod
    def query_solution_names(cls):
        names = session.query(distinct(cls.solution)).filter(
            and_(
                or_(
                    cls.owner_id == ctx.current_user.id,
                    cls.is_public.is_(True)
                ),
                cls.logical_delete_flag.is_(False)
            )
        ).all()

        results = [n[0] for n in names]

        return results

    @classmethod
    def query_solution_image_versions(cls):
        versions = session.query(distinct(cls.version)).filter(
            and_(
                or_(
                    cls.owner_id == ctx.current_user.id,
                    cls.is_public.is_(True)
                ),
                cls.logical_delete_flag.is_(False)
            )
        ).all()

        results = [v[0] for v in versions]

        return results

    @classmethod
    def query_solution_image_names(cls):
        names = session.query(distinct(cls.image)).filter(
            and_(
                or_(
                    cls.owner_id == ctx.current_user.id,
                    cls.is_public.is_(True)
                ),
                cls.logical_delete_flag.is_(False)
            )
        ).all()

        results = [n[0] for n in names]

        return results

    @classmethod
    def query_solutions(cls, solution_name=None, model_id=None, image=None, version=None,
                        my_solution=False, limit=20, offset=0):
        if my_solution:
            query_set = session.query(cls).filter(
                and_(
                    cls.owner_id == ctx.current_user.id,
                    cls.logical_delete_flag.is_(False)
                )
            )
        else:
            query_set = session.query(cls).filter(
                and_(
                    cls.is_public.is_(True),
                    cls.logical_delete_flag.is_(False)
                )
            )

        if solution_name:
            query_set = query_set.filter(cls.solution.like('%{}%'.format(solution_name)))

        if model_id:
            query_set = query_set.filter(cls.model_id == model_id)

        if image:
            query_set = query_set.filter(cls.image.like('%{}%'.format(image)))

        if version:
            query_set = query_set.filter(cls.version == version)

        query_set = query_set.order_by(desc(cls.id))
        total = query_set.count()
        solutions = query_set.offset(offset).limit(limit).all()

        return total, solutions

    @staticmethod
    def remove_object_from_bucket(bucket, key):
        s3 = boto3.client('s3')

        try:
            s3.delete_object(Bucket=bucket, Key=key)
        except Exception as e:
            err_msg = "Fail to delete solution image from S3. {}".format(str(e))
            raise DCCAException(err_msg)

    def remove(self, bucket):
        session.query(task_models.EsTaskOtaInst).filter(task_models.EsTaskOtaInst.solution_id == self.id).delete()
        t_dcca_ass_solution_tag.delete(t_dcca_ass_solution_tag.c.solution_id == self.id)
        t_dcca_ass_user_solution.delete(t_dcca_ass_user_solution.c.solution_id == self.id)
        session.query(DccaSolutionAudit).filter(DccaSolutionAudit.solution_id == self.id).delete()
        session.query(DccaSolutionSign).filter(DccaSolutionSign.solution_id == self.id).delete()
        session.query(device_models.Host).\
            filter(device_models.Host.solution_id == self.id).update({"solution_id": None})
        if self.in_s3:
            key = '/'.join(self.link.split('/')[-6:])
            self.remove_object_from_bucket(bucket, key)
        session.delete(self)

    @classmethod
    def check_solution_permission(cls, sid):
        return session.query(cls.is_public).filter(cls.id == sid).scalar()

    @classmethod
    def query_by_id(cls, solution_id):
        solution = cls.get(solution_id)
        if solution.owner == ctx.current_user or solution.is_public:
            return solution
        else:
            return None

    @classmethod
    def authorized(cls, solution_id):
        solution = cls.query_by_id(solution_id)
        if solution:
            return True
        else:
            return False


class DccaSolutionSign(Base):
    __tablename__ = 'dcca_solution_sign'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_solution_sign_id_seq'::regclass)"))
    solution_id = Column(ForeignKey('dcca_ass_solution_images.id'), nullable=False)
    key_id = Column(UUID, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("now()"))
    status = Column(SmallInteger, nullable=False, server_default=text("0"))

    solution = relationship('DccaAssSolutionImage')

    def __init__(self, solution_id, key_id, description):
        self.solution_id = solution_id
        self.key_id = key_id
        self.description = description


class DccaSolutionAudit(GetterMethodMixin, Base):
    __tablename__ = 'dcca_solution_audit'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_solution_audit_id_seq'::regclass)"))
    user_id = Column(ForeignKey(u'dcca_users.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("now()"))
    approved = Column(Boolean, nullable=False, server_default=text("false"))
    comments = Column(Text)
    solution_id = Column(ForeignKey(u'dcca_ass_solution_images.id'), nullable=False)
    status = Column(Boolean, nullable=False, server_default=text("false"))
    to_public = Column(Boolean, nullable=False, server_default=text("false"))

    solution = relationship(u'DccaAssSolutionImage')
    user = relationship(u'DccaUser')

    def __init__(self, uid, comments, solution_id, to_public):
        self.user_id = uid
        self.comments = comments
        self.solution_id = solution_id
        self.to_public = to_public

    @classmethod
    def query_audits(cls, filter_text=None, order_by=None, order_type=None, limit=20, offset=0):
        query_set = session.query(cls).outerjoin(user_models.DccaUser).filter(
            user_models.DccaUser.id == cls.user_id
        )

        if filter_text:
            query_set = query_set.filter(user_models.DccaUser.username.like('%{}%'.format(filter_text)))

        item = getattr(cls, order_by, cls.id)
        if order_type == 'asc':
            query_set = query_set.order_by(asc(item))
        else:
            query_set = query_set.order_by(desc(item))

        total = query_set.count()
        audits = query_set.offset(offset).limit(limit).all()

        return total, audits


class DccaAssModelSoftware(Base):
    __tablename__ = 'dcca_ass_model_software'

    model_id = Column(ForeignKey('dcca_models.id'), nullable=False)
    software_id = Column(ForeignKey('dcca_softwares.swid'), nullable=False)
    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_ass_model_software_id_seq'::regclass)"))

    model = relationship('DccaModel')
    software = relationship('DccaSoftware')


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


class DccaModel(OutputMixin, QueryAllMixin, Base):
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
    devices = relationship('Host', secondary='dcca_ass_host_model')

    @classmethod
    def check_model_owner(cls, mid):
        res = session.query(literal(True)).filter(
            session.query(cls.id).filter(
                and_(
                    cls.id == mid,
                    cls.owner_id == ctx.current_user.id
                )).exists()
        ).scalar()
        if res:
            return True
        else:
            return False

    @classmethod
    def check_model_permission(cls, mid):
        return session.query(cls.is_public).filter(cls.id == mid).scalar()

    @classmethod
    def is_bind_solution(cls, sid):
        res = session.query(func.count(cls.id)).filter(cls.default_solution_id == sid).scalar()

        if res:
            return True
        else:
            return False

    @classmethod
    def get_by_id(cls, _id):
        try:
            return session.query(DccaModel).filter(DccaModel.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def get_all_model(cls):
        try:
            return session.query(DccaModel).filter(
                or_(DccaModel.is_public.is_(True), DccaModel.owner_id == ctx.current_user.id)).all()
        except NoResultFound:
            return None
        # except Exception as e:
        #    print(e)

    @classmethod
    def query_by_platform(cls, platform):
        try:
            return session.query(cls).filter(cls.platform == platform).all()
        except NoResultFound:
            return None


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


class DccaMlDockerDeployment(Base):
    __tablename__ = 'dcca_ml_docker_deployment'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_ml_docker_deployment_id_seq'::regclass)"))
    status = Column(Integer, server_default=text("0"))


class DccaMlDockerTask(Base):
    __tablename__ = 'dcca_ml_docker_tasks'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_ml_docker_tasks_id_seq'::regclass)"))
    code = Column(Text)
    status = Column(Integer, server_default=text("0"))


class DccaAIEngine(OutputMixin, Base):
    """
    The AI engines
    """
    __tablename__ = 'dcca_ai_engines'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v1mc()"))
    name = Column(String(32), nullable=False)
    category = Column(Enum('training', 'interference', name='engine'), nullable=False)
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
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
    def get(cls, _id):
        """
        Get by ID, no auth check
        """
        return cls._query_by_id(_id)

    @classmethod
    def get_all(cls, ids):
        return session.query(cls).filter(cls.id.in_(ids)).all()

    @classmethod
    def _query_by_id(cls, _id):
        try:
            return session.query(cls).filter(cls.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).filter(and_(cls.id == _id, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def query_all(cls):
        engines = session.query(cls).filter(
            or_(
                cls.is_public.is_(True),
                and_(
                    cls.is_public.is_(False),
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
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
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
    def get(cls, _id):
        try:
            return session.query(cls).filter(cls.id == _id).one()
        except NoResultFound:
            return None

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).filter(and_(cls.id == _id, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def query_by_name(cls, name):
        try:
            return session.query(cls).filter(and_(cls.name == name, cls.owner == ctx.current_user)).one()
        except NoResultFound:
            return None

    @classmethod
    def query_bulk_startswith_name(cls, name, reverse=False):
        query_set = session.query(cls).filter(
            and_(
                cls.name == name,
                cls.owner == ctx.current_user
            )
        )

        if reverse:
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
                cls.is_public.is_(True),
                cls.owner == ctx.current_user
            )
        )

        if filter_name:
            query_set = query_set.filter(cls.name.like(filter_name + '%'))

        if fnt or fni:
            query_set = query_set.outerjoin(t_dcca_ass_ai_model_engine).filter(
                DccaAIModel.id == t_dcca_ass_ai_model_engine.c.model_id) \
                .outerjoin(DccaAIEngine).filter(t_dcca_ass_ai_model_engine.c.engine_id == DccaAIEngine.id)
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

    @staticmethod
    def valid_training_engine(engine):
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

    @staticmethod
    def valid_interference_engines(engines):
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
