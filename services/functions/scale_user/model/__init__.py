# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import psycopg2

import boto3
from DBUtils.PooledDB import PooledDB
from sqlalchemy import create_engine

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
SMTP_HOST = config['SMTP_HOST']
SMTP_PORT = config['SMTP_PORT']
ADMIN_EMAIL = config['ADMIN_EMAIL']
ADMIN_EMAIL_PWD = config['ADMIN_EMAIL_PWD']
IS_DEBUG = config["DEBUG"]

engine_url = 'postgresql://{username}:{pwd}@{host}:{port}/{db}'.format(
    username=USER, pwd=PASSWORD, host=DB_HOST, port=DB_PORT, db=DATABASE
)

engine = create_engine(engine_url, pool_size=10)
session.configure(bind=engine)

