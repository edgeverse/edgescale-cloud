# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import gevent 
import logging
import time
import os 
from gevent.queue import Queue, Empty
from sqlalchemy import create_engine

from models import *
from constants import _LIMIT, _OFFSET
from utils import *

#format logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('schedular.log'),
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

#Init tasks queue
tasksQueue = Queue()


logger = logging.getLogger('DAUpdater')

def put_work():
    #qury new tasks 
    tasks = EsTask.query_da_tasks(limit=_LIMIT, offset=_OFFSET)
    logger.info("===========  Schedular started, {}  ===========".format(len(tasks)))
    for task in tasks:
        tasksQueue.put(task)


def get_work():
    try:
        while True:
            workInfo = tasksQueue.get(timeout=0.1)
            logger.info("Start to parse task, {}".format(workInfo.id))
            # Query all task sub instances
            inst_list = EsTaskDaInst.task_inst(workInfo, limit=_LIMIT, offset=_OFFSET)
            for inst in inst_list:
                logger.info('  Instance: {}, status: {} '.format(inst.id, DA_TASK_STATUS_NAMES[inst.status]))
            latest_status = EsTask.parse_status([i.status for i in inst_list])
            if workInfo.status != latest_status:
                try:
                    workInfo.status = latest_status
                    session.add(workInfo)
                    session.commit()
                    logger.info('  Task status changed to {}.'.format(TASK_STATUS_NAMES[workInfo.status]))
                except Exception as e:
                    session.rollback()
                    raise Exception(e.message)
            else:
                logger.info('  Status no change, {}.'.format(TASK_STATUS_NAMES[workInfo.status]))
    except Empty:
        return


gevent.spawn(put_work).join()
gevent.joinall([gevent.spawn(get_work),gevent.spawn(get_work),gevent.spawn(get_work)])
