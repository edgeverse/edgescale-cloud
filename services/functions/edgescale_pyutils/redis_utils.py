# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import redis

from edgescale_pyutils.exception_utils import DCCAException


class RedisConnectError(object):
    def __getattr__(self, item):
        raise DCCAException("Redis Error.")

    def __getattribute__(self, item):
        raise DCCAException("Redis Error.")


def connect_redis(host, port=6379, pwd=''):
    try:
        pool = redis.ConnectionPool(host=host, port=port, password=pwd, max_connections=100, decode_responses=True)
        redis_client = redis.StrictRedis(connection_pool=pool, socket_connect_timeout=3, socket_timeout=3)
        redis_client.ping()
    except Exception as e:
        print("Redis connection failed. Error:", str(e))
        return RedisConnectError()
    return redis_client
