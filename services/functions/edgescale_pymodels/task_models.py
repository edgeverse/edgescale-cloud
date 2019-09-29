# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

# coding: utf-8
import unicodedata
import uuid
import os

import requests
from paho.mqtt import publish
from sqlalchemy import Integer, text, JSON, DateTime, Boolean, SmallInteger, String, Text
from sqlalchemy.orm import relationship

from edgescale_pymodels.constants import CERTS, DA_TASK_STATUS_FAILED, DA_TASK_STATUS_READY, TASK_TYPE_NAMES, \
    TASK_TYPE_SOLUTION, TASK_STATUS_READY, COMMON_TASK_STATUS
from edgescale_pymodels import constants
from edgescale_pymodels import app_models
from edgescale_pymodels import device_models
from edgescale_pymodels import solution_models
from edgescale_pymodels.base_model import *
from edgescale_pyutils.exception_utils import DCCAException, InvalidParameterException


class QueryTaskInstMixin(object):
    @classmethod
    def query_inst(cls, task):
        return session.query(cls).filter(cls.task == task).all()


class QueryTaskDeviceMixin(object):
    @classmethod
    def query_devices(cls, task):
        devices = set()
        instances = cls.query_inst(task)
        for inst in instances:
            devices.add(inst.device)
        return devices


class QueryInIdLogicalMinx(object):
    @classmethod
    def query_in(cls, ids):
        return session.query(cls).filter(
            and_(cls.id.in_(ids),
                 cls.owner == ctx.current_user,
                 cls.logical_delete.is_(False)
                 )).all()


class EsOtaTaskHelperMinxin(object):
    @classmethod
    def todo(cls):
        return 'hello, world'

    @classmethod
    def _mqtt_topic_by_name(cls, name):
        topic = 'edgescale/device/{}'.format(name)
        if os.getenv('mqtopic') == 'v1':
            topic = 'device/{}'.format(name)

        return topic

    def _mqtt_req_topic(self):
        topic = 'edgescale/device/{}'.format(self.device.name)
        if os.getenv('mqtopic') == 'v1':
            topic = 'device/{}'.format(self.device.name)

        return topic

    @classmethod
    def publish(cls, mqtt_host, payload, name):
        topic = cls._mqtt_topic_by_name(name)
        publish.single(topic, json.dumps(payload), qos=2, hostname=mqtt_host)

    def publish_message(self, mqtt_host, payload, ):
        try:
            topic = self._mqtt_req_topic()
            publish.single(topic, json.dumps(payload), qos=2, hostname=mqtt_host)
            self.status = constants.OTA_TASK_CODE_START
        except Exception:
            raise DCCAException('Fail to public message to device.')


class EsTaskHelperMinxin(object):
    @classmethod
    def _container_template(cls):
        return {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "<app_name>", "labels": {"name": "<app_name>"}},
                "spec": {"hostNetwork": True, "containers": [
                    {"name": "<app_name>", "image": "<docker_repo/app_name:version>",
                     "imagePullPolicy": "IfNotPresent", "securityContext": {"privileged": True}}],
                         "nodeSelector": {"kubernetes.io/hostname": "<device_id>"},
                         "imagePullSecrets": [{"name": "secret"}]}}

    def _mk_name(self):
        return '{name}-{hex}'.format(name=self.softapp.application.name.strip().lower(),
                                     hex=uuid.uuid4().hex)

    @classmethod
    def _jsonfy_commands(cls, commands):
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

    @classmethod
    def _valid_ports_filter(cls, ports):
        valid_ports = []
        for port in ports:
            if port['containerPort'] and port['hostPort']:
                valid_ports.append(port)
        return valid_ports

    def _param_ports_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_ports'):
            ports = self.payload['parameters'].get('dynamic_ports')
            p = self._valid_ports_filter(ports)
            return p if p else self._valid_ports_filter(self.softapp.ports)
        else:
            return self._valid_ports_filter(self.softapp.ports)

    def _param_cap_add_filter(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_cap_add'):
            return self.payload['parameters'].get('dynamic_cap_add')
        else:
            return self.softapp.cap_add

    def _param_resources_filter(self):
        def validate_resource(resource):
            limits = {}
            if not resource:
                return
            try:
                if 'cpu' in resource:
                    float(resource['cpu'])
                    limits['cpu'] = resource['cpu']
            except Exception:
                raise Exception('cpu should be float')

            try:
                if 'memory' in resource:
                    # backcompatible database
                    if 'M' in resource['memory']:
                        resource['memory'] = resource['memory'] \
                            .split('M')[0]
                    int(resource['memory'])
                    # resource unit is MiByte
                    limits['memory'] = resource['memory'] + "Mi"
            except Exception:
                raise Exception('memory should be int')
            return limits

        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_resources'):
            r = self.payload['parameters'].get('dynamic_resources')
        else:
            try:
                r = self.softapp.morepara.get('resources')
            except Exception:
                r = {}
        return validate_resource(r)

    def _param_env_filter(self):
        try:
            r = self.softapp.morepara.get('env')
        except:
            r = []
        if not isinstance(r, list):
            r = []

        # Append default envrionment
        r.append({"name": "ES_DEVICEID", "value": self.device.name})

        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_env'):
            r0 = []
            try:
                env = self.payload['parameters'].get('dynamic_env')
                for e in env:
                    if 'name' in e and "value" in e:
                        if e["name"].strip() != "":
                            r0.append({"name": e["name"], "value": e["value"]})
                    else:
                        raise InvalidParameterException('env should use keys name and value')
            except Exception as e:
                raise Exception(str(e))

            r += r0
        if len(r) > 0:
            return r
        return False

    def _param_volumns_filter_v0(self):
        if self.is_valid_parameter(self.payload['parameters'], 'dynamic_volumes'):
            volumes = self.payload['parameters'].get('dynamic_volumes')
            for v in volumes:
                if self.is_valid_parameter(v, 'hostPath') and self.is_valid_parameter(v, 'mountPath'):
                    return volumes
        return []

    def _param_volumn_mounts_filter_v0(self):
        if self.is_valid_parameter(self.payload['parameters'], ''):
            pass  # TODO

    def _param_volumns_filter(self):
        """
        "dynamic_volumes": [{"hostPath": {"path": ""}, "name": ""}],
        "dynamic_volumeMounts": [{"readOnly": true, "mountPath": "", "name": ""}]
        """
        volumes = self._param_volumns_filter_v0()
        # Use the default
        if not volumes:
            v = self.softapp.volume_mounts
            if v and isinstance(v, list) and self.is_valid_parameter(v[0], 'mountPath'):
                return self.softapp.volumes, self.softapp.volume_mounts

        # Use dynamic_volumes, dynamic_volumeMounts
        dynamic_volumes = []
        dynamic_volume_mounts = []
        for _index, volume in enumerate(volumes):
            host_path = volume['hostPath']
            mount_path = volume['mountPath']
            if host_path and mount_path:
                pass
            else:
                continue

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
        registry = self.softapp.registry.name
        if registry == 'hub.docker.com':
            is_docker_hub = True
        else:
            is_docker_hub = False

        # The parameters filter
        commands = self._param_commands_filter()
        args = self._param_args_filter()
        host_network = self._param_host_network_filter()
        ports = self._param_ports_filter()
        volumes, volume_mounts = self._param_volumns_filter()  # TODO
        cap_add = self._param_cap_add_filter()
        resources = self._param_resources_filter()
        env = self._param_env_filter()

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

        if commands and len(commands) > 0:
            o['spec']['containers'][0]['command'] = json.loads(commands)

        if args and len(args) > 0:
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

        if resources:
            o['spec']['containers'][0]['resources'] = {'limits': resources}

        if env:
            o['spec']['containers'][0]['env'] = env

        return json.dumps(o)

    def _deploy_url_maker(self, host, port):
        return constants.RESOURCE_DEPLOY_APP.format(dns=host, port=port, uid=self.task.owner.id)

    def _query_url_maker(self, host, port, name):
        return constants.RESOURCE_QUERY_APP_STATUS.format(dns=host, port=port, uid=self.task.owner.id, name=name)

    @classmethod
    def _k8s_filter(cls, content):
        if isinstance(content, (str, bytes)):
            ps = json.loads(content)
        else:
            ps = content

            # Return if http code is not 0
        if 'code' in ps and ps['code'] != 0:
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
        """
        DA_TASK_STATUS_UNKNOWN = -1
        DA_TASK_STATUS_READY = 0
        DA_TASK_STATUS_PENDING = 1
        DA_TASK_STATUS_CREATING = 2
        DA_TASK_STATUS_STARTING = 3
        DA_TASK_STATUS_FAILED = 4
        DA_TASK_STATUS_RUNNING = 5
        DA_TASK_STATUS_DELETING = 6
        DA_TASK_STATUS_DELETED = 7
        DA_TASK_STATUS_TIMEOUT = 8
        DA_TASK_STATUS_ERROR = 9
        """
        if status == 'Pending':
            return constants.DA_TASK_STATUS_PENDING
        elif status == 'Creating':
            return constants.DA_TASK_STATUS_CREATING
        elif status == 'Starting':
            return constants.DA_TASK_STATUS_STARTING
        elif status == 'Failed':
            return constants.DA_TASK_STATUS_FAILED
        elif status == 'Running':
            return constants.DA_TASK_STATUS_RUNNING
        elif status == 'Deleting':
            return constants.DA_TASK_STATUS_DELETING
        elif status == 'Deleted':
            return constants.DA_TASK_STATUS_DELETED
        else:
            return constants.DA_TASK_STATUS_UNKNOWN


class TaskStatisticsMixin(object):
    @classmethod
    def statistics(cls, task, mapping):
        results = OrderedDict()
        results['data'] = {}

        devices = set()
        inst_list = cls.query_inst(task)
        for inst in inst_list:
            if inst.status in list(mapping.keys()):
                status = mapping[inst.status]
            else:
                status = constants.DA_TASK_STATUS_FAILED_MSG if inst.task.type == constants.TASK_TYPE_APP else constants.OTA_TASK_STATUS_UNKNOWN

            if status not in results['data']:
                results['data'][status] = 1
            else:
                results['data'][status] += 1
            devices.add(inst.device.id)

        for code, name in mapping.items():
            if name not in results['data']:
                results['data'][name] = 0

        results['total'] = len(inst_list)
        results['devices'] = len(devices)
        return results


TASK_TYPE_DA = 0
TASK_TYPE_OTA = 1
TASK_STATUS_READY_TO_START = 0
TASK_STATUS_STARTED = 1


class DccaCiTask(Base):
    __tablename__ = 'dcca_ci_tasks'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dcca_ci_tasks_id_seq'::regclass)"))
    code = Column(String(255), nullable=False)
    status = Column(Integer, server_default=text("0"))


class EdgescaleTask(Base):
    __tablename__ = 'edgescale_tasks'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('edgescale_tasks_id_seq'::regclass)"))
    type = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Integer)
    timestamp = Column(DateTime, server_default=text("now()"))
    logical_delete = Column(Boolean, nullable=False, server_default=text("false"))
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)

    owner = relationship('DccaUser')
    users = relationship('DccaUser', secondary='dcca_ass_user_task')
    devices = relationship('DccaAssDeviceTask', primaryjoin='EdgescaleTask.id==DccaAssDeviceTask.task_id')

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).outerjoin(t_dcca_ass_user_task).filter(cls.id == t_dcca_ass_user_task.c.task_id) \
                .filter(and_(t_dcca_ass_user_task.c.user_id == ctx.current_user.id,
                             t_dcca_ass_user_task.c.task_id == _id,
                             cls.logical_delete.is_(False))).one()
        except NoResultFound:
            return None

    @classmethod
    def binded_devices(cls, task_id):
        return session.query(device_models.Host).outerjoin(device_models.DccaAssDeviceTask). \
            filter(device_models.Host.id == device_models.DccaAssDeviceTask.device_id) \
            .filter(device_models.DccaAssDeviceTask.task_id == task_id).all()

    @classmethod
    def query_all_da(cls, limit=2000, offset=0):
        return session.query(cls) \
            .filter(
            and_(
                cls.type == TASK_TYPE_DA,
                ~cls.status.in_(
                    [constants.TASK_STATUS_CANCELED, constants.TASK_STATUS_FAIL, constants.TASK_STATUS_COMPLETE]),
                cls.logical_delete.is_(False))) \
            .limit(limit).offset(offset).all()


class EsTask(OutputMixin, QueryInIdLogicalMinx, Base):
    __tablename__ = 'es_tasks'

    id = Column(Integer, primary_key=True, unique=True, server_default=text("nextval('es_tasks_id_seq'::regclass)"))
    type = Column(SmallInteger, nullable=False, server_default=text("0"))
    status = Column(SmallInteger, nullable=False, server_default=text("0"))
    payloads = Column(JSON, nullable=False)
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    logical_delete = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    started_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    ended_at = Column(DateTime, nullable=True)

    owner = relationship('DccaUser')

    # instances = relationship('EsTaskInstance', primaryjoin='es_tasks.id==es_task_instances.task_id')

    def __init__(self, _type, payloads):
        self.type = _type
        self.status = constants.TASK_STATUS_READY
        self.payloads = payloads
        self.owner = ctx.current_user

    @classmethod
    def query_all(cls, status=None, device_id=None, limit=20, offset=0, order_by='created_at', reverse=True):
        if device_id:
            tasks = EsTask.query_by_device(device_id)
            return tasks, len(tasks)

        query_set = session.query(cls).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.logical_delete.is_(False)
            ))

        if status is not None and status in constants.TASK_STATUS:
            query_set = query_set.filter(cls.status == status)

        if order_by:
            item = getattr(cls, order_by, cls.id)
            if reverse:
                query_set = query_set.order_by(desc(item))
            else:
                query_set = query_set.order_by(item)

        total = query_set.count()
        query_set = query_set.limit(limit).offset(offset)
        # print_raw_sql(query_set)
        return query_set.all(), total

    @classmethod
    def query_da_many(cls, limit=2000):
        return session.query(cls).filter(
            and_(cls.type == constants.TASK_TYPE_APP,
                 cls.owner == ctx.current_user,
                 cls.logical_delete.is_(False))) \
            .limit(limit).all()

    @classmethod
    def query_by_id(cls, _id):
        try:
            return session.query(cls).filter(
                and_(cls.id == _id, cls.owner == ctx.current_user, cls.logical_delete.is_(False))).one()
        except NoResultFound:
            return None

    @classmethod
    def sync_owner(cls):
        tasks = session.query(cls).all()
        for task in tasks:
            task.owner = task.users[0]

    @classmethod
    def query_many(cls, limit=20, offset=0):
        query_set = session.query(cls).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.logical_delete.is_(False)
            ))
        size = query_set.count()
        tasks = query_set.limit(limit).offset(offset).all()
        return tasks, size

    @classmethod
    def check_da_payload(cls, payloads):
        unauthorized = []

        for pl in payloads:
            app_id = pl['application_id']
            if 'version' not in pl:
                unauthorized.append(app_id)
                continue

            version = pl['version']
            softapp = app_models.DccaSoftapp.query_one(app_id, version)
            if not app_models.DccaApplication.authorized(app_id) or not softapp:
                unauthorized.append(app_id)
            else:
                pl['softapp_id'] = softapp.id
        return unauthorized

    @classmethod
    def check_ota_payload(cls, payload):
        solution_id = payload['solution_id']
        solution = solution_models.DccaAssSolutionImage.query_by_id(solution_id)
        if not solution:
            return False, None
        else:
            return True, solution

    @classmethod
    def create_da_task(cls, payloads):
        return cls(_type=constants.TASK_TYPE_APP, payloads=payloads)

    @classmethod
    def create_ota_task(cls, payloads):
        return cls(_type=constants.TASK_TYPE_SOLUTION, payloads=payloads)

    @classmethod
    def create_common_task(cls, task_type, payloads):
        return cls(_type=task_type, payloads=payloads)

    def common_inst(self, device, payload):
        """
        Generate a common task instance
        """
        return EsTaskDevicesInst(self, device, payload)

    def start(self, deploy_url, params, data=None):
        try:
            _ = requests.post(deploy_url, params=params, data=data, cert=CERTS, verify=False, timeout=7)
        except Exception:
            self.status = DA_TASK_STATUS_FAILED
        else:
            self.status = DA_TASK_STATUS_READY

    def da_inst(self, device, softapp, payload):
        """
        Generate da task instance
        """
        return EsTaskDaInst(self, device, softapp, payload)

    def ota_inst(self, device, solution):
        return EsTaskOtaInst(self, device, solution)

    def query_task_devices(self):
        if self.type == constants.TASK_TYPE_APP:
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
                cls.logical_delete.is_(False),
                EsTaskDaInst.device_id == device_id
            )
        ).all()

        ota_tasks = session.query(cls).outerjoin(
            EsTaskOtaInst, cls.id == EsTaskOtaInst.task_id
        ).filter(
            and_(
                cls.owner == ctx.current_user,
                cls.logical_delete.is_(False),
                EsTaskOtaInst.device_id == device_id
            )
        ).all()
        return da_tasks + ota_tasks

    def as_inst_dict(self):
        if self.type == constants.TASK_TYPE_APP:
            inst_list = EsTaskDaInst.query_inst(self)
        elif self.type == constants.TASK_TYPE_SOLUTION:
            inst_list = EsTaskOtaInst.query_inst(self)
        else:
            inst_list = EsTaskDevicesInst.query_inst(self)

        devices = {}
        for inst in inst_list:
            device_id = inst.device.id
            if self.type == constants.TASK_TYPE_APP:
                status_payload = EsTaskDaInst.payload_filter(inst.status_payload)
            elif self.type == constants.TASK_TYPE_SOLUTION:
                status_payload = OrderedDict()
                status_payload['id'] = inst.solution.id
                status_payload['name'] = inst.solution.solution
                status_payload['status'] = constants.OTA_STATUS_MAP[inst.status]
            else:
                status_payload = OrderedDict()
                status_payload['id'] = inst.id
                status_payload['name'] = TASK_TYPE_NAMES[self.type]
                status_payload['status'] = COMMON_TASK_STATUS[int(inst.status)]
                status_payload['result'] = inst.result

            if inst.device.id not in devices:
                devices[device_id] = {}
                devices[device_id]['name'] = inst.device.name
                devices[device_id]['payloads'] = [status_payload]
            else:
                devices[device_id]['payloads'].append(status_payload)

        data = []
        for device_id, item in devices.items():
            device = OrderedDict()
            device['device_id'] = device_id
            device['device_name'] = item['name']
            device['payloads'] = item['payloads']
            data.append(device)
        return data

    def statistics(self):
        if self.type == constants.TASK_TYPE_APP:
            return EsTaskDaInst.statistics(self, constants.DA_TASK_STATUS_NAMES_SHOWN)
        elif self.type == TASK_TYPE_SOLUTION:
            return EsTaskOtaInst.statistics(self, constants.OTA_STATUS_MAP)
        else:
            return EsTaskDevicesInst.statistics(self, COMMON_TASK_STATUS)


class EsTaskDaInst(GetterMethodMixin, QueryTaskInstMixin, QueryTaskDeviceMixin, EsTaskHelperMinxin,
                   TaskStatisticsMixin, Base):
    __tablename__ = 'es_task_da_inst'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    task_id = Column(ForeignKey('es_tasks.id'))
    device_id = Column(ForeignKey('hosts.id'), nullable=False)
    softapp_id = Column(ForeignKey('dcca_softapps.id'))
    status = Column(SmallInteger, nullable=False, server_default=text("0"))
    status_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, server_default=text("timezone('utc'::text, now())"))
    payload = Column(JSON, nullable=False)

    device = relationship('Host')
    task = relationship('EsTask')
    softapp = relationship('DccaSoftapp')

    def __init__(self, task, device, softapp, payload):
        self.task = task
        self.device = device
        self.softapp = softapp
        self.status = constants.DA_TASK_STATUS_PENDING
        self.status_payload = {}
        self.payload = payload

    # @classmethod
    # def query_inst(cls, task, limit=2000, offset=0):
    #     return session.query(cls).filter(
    #         and_(~cls.status.in_([DA_TASK_STATUS_FAILED, DA_TASK_STATUS_DELETING,
    #                          DA_TASK_STATUS_DELETED, DA_TASK_STATUS_TIMEOUT,
    #                          DA_TASK_STATUS_ERROR]), cls.task == task)
    #     ).limit(limit).offset(offset).all()

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
        deploy_url = self._deploy_url_maker(host, port)
        params = {'taskid': str(self.task_id)}
        try:
            resp = requests.post(deploy_url, data=t, params=params, cert=constants.CERTS, verify=False, timeout=7)
        except Exception:
            self.status = constants.DA_TASK_STATUS_K8S_NO_RESPONSE
        else:
            self.status_payload = self._k8s_filter(resp.content)
            self.status = constants.DA_TASK_STATUS_PENDING

    def update_status(self, host, port):
        status_payload = self.status_payload
        if 'code' in status_payload:
            name = status_payload['items'][0]['metadata']['name']

            # Fetch k8s status and save
            query_status_url = self._query_url_maker(host, port, name)
            try:
                resp = requests.get(query_status_url, cert=constants.CERTS,
                                    headers=constants.HEADERS, verify=False, timeout=7)
            except requests.Timeout:
                raise Exception('The k8s timeout exception.')
            self.updated_at = datetime.utcnow()
            self.status_payload = json.loads(resp.content)
            latest_status = self.status_payload['items'][0]['status']['phase']
            if self.status != latest_status:
                self.status = self._status_filter(latest_status)
        else:
            raise Exception('Unknown, %s' % (json.dumps(status_payload)))
        return self.status_payload

    @classmethod
    def payload_filter(cls, payload):
        if 'code' in payload:
            new_pl = OrderedDict()
            new_pl['code'] = payload['code']
            new_pl['apiVersion'] = payload['apiVersion']
            if 'items' in payload and payload['items']:
                new_pl['metadata'] = payload['items'][0]['metadata']
                new_pl['status'] = payload['items'][0]['status']
            else:
                new_pl['metadata'] = {}
                new_pl['status'] = {}
            return new_pl
        elif not payload:
            return payload
        else:
            return payload

    @classmethod
    def query_all(cls):
        return session.query(cls).all()


class EsTaskDevicesInst(GetterMethodMixin, QueryTaskInstMixin, QueryTaskDeviceMixin,
                        EsTaskHelperMinxin, TaskStatisticsMixin, Base):
    __tablename__ = 'es_task_device_inst'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    task_id = Column(ForeignKey(u'es_tasks.id'))
    device_id = Column(ForeignKey(u'hosts.id'), nullable=False)
    status = Column(SmallInteger, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, server_default=text("timezone('utc'::text, now())"))
    payload = Column(JSON)
    result = Column(Text)

    device = relationship(u'Host')
    task = relationship(u'EsTask')

    def __init__(self, task, device, payload):
        self.task = task
        self.device = device
        self.status = TASK_STATUS_READY
        self.payload = payload

    @classmethod
    def payload_filter(cls, payload):
        return payload

    @classmethod
    def query_all(cls):
        return session.query(cls).all()


class EsTaskOtaInst(QueryTaskInstMixin, GetterMethodMixin, QueryTaskDeviceMixin,
                    TaskStatisticsMixin, EsOtaTaskHelperMinxin, Base):
    __tablename__ = 'es_task_ota_inst'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    task_id = Column(ForeignKey('es_tasks.id'), nullable=False)
    device_id = Column(ForeignKey('hosts.id'), nullable=False)
    solution_id = Column(ForeignKey('dcca_ass_solution_images.id'), nullable=False)
    status = Column(SmallInteger, nullable=False)
    status_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))

    device = relationship('Host')
    solution = relationship('DccaAssSolutionImage')
    task = relationship('EsTask')

    def __init__(self, task, device, solution):
        self.task = task
        self.device = device
        self.solution = solution
        self.status = constants.OTA_TASK_CODE_START
        self.status_payload = {}

    @classmethod
    def query_devices(cls, task):
        devices = set()
        instances = cls.query_inst(task)
        for inst in instances:
            devices.add(inst.device)
        return devices

    def start(self, mqtt_host):
        payload = {
            'action': 'update_firmware',
            'mid': self.id,
            'solutionid': self.solution.id,
            'solution': self.solution.solution,
            'model_id': self.solution.model_id,
            'version': self.solution.version,
            'url': self.solution.link,
        }

        self.publish_message(mqtt_host, payload)

    def record(self):
        # TODO make records in redis
        pass

    # @classmethod
    # def query_inst(cls, limit=2000, offset=0):
    #     return session.query(cls).filter(
    #         ~cls.status.in_([OTA_TASK_CODE_DONE])
    #     ).limit(limit).offset(offset).all()

    def update_status(self):
        if self.status != self.task.status:
            self.task.status = self.status
            if self.status == constants.OTA_TASK_CODE_COMPLETE:
                self.status = constants.OTA_TASK_CODE_DONE


class DccaTaskStatus(Base):
    __tablename__ = 'dcca_task_status'

    id = Column(Integer, primary_key=True, unique=True,
                server_default=text("nextval('dcca_task_status_id_seq'::regclass)"))
    name = Column(String(10), nullable=False)


TEMPLATE_TYPE_APP = 0
TEMPLATE_TYPE_SOLUTION = 1


class DccaTaskTemplate(OutputMixin, Base):
    __tablename__ = 'dcca_task_templates'

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1mc()"))
    owner_id = Column(ForeignKey('dcca_users.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    updated_at = Column(DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
    name = Column(String(32), nullable=False)
    body = Column(JSON)
    desc = Column(Text, nullable=False)

    owner = relationship('DccaUser')
    devices = relationship(
        'Host',
        secondary=t_dcca_ass_template_device
    )

    # def bind_devices(self, devices):
    #     for device in devices:
    #         self.devices.append(device)
    #
    # def app_schema(self):
    #     schemas = []
    #     for pl in self.body.get("payload", []):
    #         app_id = pl['application_id']
    #         app = app_models.DccaApplication.get(app_id)
    #         schema = OrderedDict()
    #         schema['id'] = app_id
    #         schema['name'] = app.name
    #         schema['version'] = pl['version']
    #
    #         schemas.append(schema)
    #
    #     return schemas
    #
    # def solution_schema(self):
    #     pass
    #
    # def object_as_dict(self):
    #     result = self.as_dict(schema=TemplateAppSchema)
    #     schema = self.app_schema()
    #     return {}
    #
    # def make_result(self, task):
    #     app_data = self.app_schema()
    #
    #     result = OrderedDict()
    #     result['status'] = 'success'
    #     result['message'] = 'Success to create task template'
    #     result['template'] = self.as_dict(schema=TemplateAppSchema)
    #
    #     # TODO pagination
    #     result['template']['schema'] = {}
    #     result['template']['schema']['applications'] = OrderedDict()
    #     result['template']['schema']['applications']['total'] = len(app_data)
    #     result['template']['schema']['applications']['offset'] = 0
    #     result['template']['schema']['applications']['limit'] = len(app_data)
    #     result['template']['schema']['applications']['items'] = app_data
    #
    #     # TODO pagination
    #     result['template']['schema']['devices'] = OrderedDict()
    #     result['template']['schema']['devices']['total'] = 0
    #     result['template']['schema']['devices']['offset'] = 0
    #     result['template']['schema']['devices']['limit'] = 0
    #     result['template']['schema']['devices']['items'] = 0


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
    status = relationship('DccaTaskStatus')
    type = relationship('DccaTaskType')
