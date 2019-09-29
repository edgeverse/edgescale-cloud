# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from sqlalchemy.dialects import postgresql

from edgescale_pyutils.exception_utils import DCCAException


class ReqContext(object):
    current_user = None


ctx = ReqContext()


def print_raw_sql(query_set):
    raw_sql_str = str(query_set.statement.compile(dialect=postgresql.dialect()))
    print(raw_sql_str)
    return raw_sql_str


def as_dict(objects=None, schema=None, many=False):
    if not objects or not schema:
        raise DCCAException("objects or schema is empty!")

    if many:
        results = schema(many=True).dump(objects)
    else:
        results = schema().dump(objects)

    return results.data
