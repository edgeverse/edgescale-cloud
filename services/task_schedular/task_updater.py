# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import gevent 
import logging
import time
import os 
from sqlalchemy import create_engine
from gevent.queue import Queue, Empty

from models import *
from constants import _LIMIT, _OFFSET
from utils import *

#format logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('updater.log'),
    ]
)
#get database info from env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT","5432")
DATABASE = os.getenv("DATABASE","edgescale")
USER = os.getenv("DB_USER","root")
PASSWORD = os.getenv("DB_PASSWORD","edgescale")


#init database session
engine_url = 'postgresql://{username}:{pwd}@{host}:{port}/{db}'.format(
    username=USER, pwd=PASSWORD, host=DB_HOST, port=DB_PORT, db=DATABASE
)
engine = create_engine(engine_url, echo=False)
session.configure(bind=engine)
try:
    connection = engine.connect()
    result = connection.execute("select text from config").fetchone()[0]
    config = result.get("settings")
    K8S_HOST = config['K8S_HOST']
    K8S_PORT = config['K8S_PORT']
except Exception as e:
    print("Database connection failed. Error:", str(e))
finally:
    connection.close()

#Init tasks queue
instancesQueue = Queue()

logger = logging.getLogger('DAUpdater')

def put_work():
    #qury new sub task instances 
    instances = EsTaskDaInst.query_inst(limit=_LIMIT, offset=_OFFSET)
    logger.info('Start, all {0} need to sychronise'.format(len(instances)))
    for inst in instances:
        instancesQueue.put(inst)


def get_work():
    try:
        while True:
            instanceInfo = instancesQueue.get(timeout=0.1)
            try:
                instanceInfo.update_status(host=K8S_HOST, port=K8S_PORT)
                session.add(instanceInfo)
            except DCCAException as e:
                session.rollback()
            except Exception as e:
                print(e.message)
                session.rollback()
                continue
            else:
                session.commit()
    except Empty:
        return


if __name__ == "__main__":
    gevent.spawn(put_work).join()
    gevent.joinall([gevent.spawn(get_work),gevent.spawn(get_work),gevent.spawn(get_work)])
