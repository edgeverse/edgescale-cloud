# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import psycopg2

import boto3
from DBUtils.PooledDB import PooledDB
from sqlalchemy import create_engine

from edgescale_pyutils.redis_utils import connect_redis
from edgescale_pymodels.base_model import session

# config data from postgres
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT","5432")
DATABASE = os.getenv("DATABASE","edgescale")
USER = os.getenv("DB_USER","root")
PASSWORD = os.getenv("DB_PASSWORD")

try:
    es_pool = PooledDB(
        creator=psycopg2,
        maxconnections=100,
        mincached=10,
        maxcached=10,
        maxusage=None,  # maximum number of reuses of a single connection
        host=DB_HOST,
        port=DB_PORT,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )
    config_conn = es_pool.connection()
    config_cur = config_conn.cursor()
    sql = "select text from config"
    config_cur.execute(sql)
    config = config_cur.fetchone()[0].get("settings")
except Exception as e:
    print("Database connection failed. Error:", str(e))
    es_pool = None
finally:
    config_cur.close()
    config_conn.close()

HOST_SITE = config['HOST_SITE']

IS_DEBUG = config["DEBUG"]

# The k8s
K8S_HOST = config['K8S_HOST']
K8S_PORT = config['K8S_PORT']

DEVICE_TABLE = config.get('ENROLL_DEVICE_TABLE', 'edgescale-devices-dev')

# The mqtt
MQTT_LOCAL_HOST = config['MQTT_LOCAL_HOST']
MQTT_MGMT_USER = config['MQTT_MGMT_USER']
MQTT_MGMT_PASS = config['MQTT_MGMT_PASS']
MQTT_HOST = config['MQTT_HOST']

S3_LOG_URL = config['LOG_URL']

API_URI = config["API_URI"]
MQTT_URI = config["MQTT_URI"]
docker_content_trust_server = config["DOCKER_CONTNET_TRUST"]

device_status_table = config['DEVICE_STATUS_TABLE']

REDIS_HOST = config['REDIS_HOST']
REDIS_PORT = config['REDIS_PORT']
REDIS_PWD = config['REDIS_PWD']
REST_API_ID = config['REST_API_ID']
SHORT_REST_API_ID = config['REST_API_SHORT_ID']
REDIS_KEY_CREATE_DEVICE_FORMAT = '{rest_api_id}:{user_id}:{datetime}:cd'

engine_url = 'postgresql://{username}:{pwd}@{host}:{port}/{db}'.format(
    username=USER, pwd=PASSWORD, host=DB_HOST, port=DB_PORT, db=DATABASE
)

engine = create_engine(engine_url, pool_size=10)
session.configure(bind=engine)

redis_client = connect_redis(REDIS_HOST, port=REDIS_PORT, pwd=REDIS_PWD)
