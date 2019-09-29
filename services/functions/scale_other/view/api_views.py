# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from edgescale_pymodels.constants import UNAUTH_RESULT
from edgescale_pyutils.view_utils import get_oemid
from model.constants import DATE_TIME_DAY_FORMAT
from utils import validate_time, calculate_delta, clock_time_filter, validate_datetime_format, query_api_usage

api_bp = Blueprint("api", __name__)


@api_bp.route("/usage", methods=["GET"])
def query_api_usage_statistics():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    start_utc_time = request.args.get('start_utc_time')
    end_utc_time = request.args.get('end_utc_time')

    result = validate_time(start_utc_time, end_utc_time)
    if result['status'] == 'fail':
        return jsonify(result)

    records = calculate_delta(request.cursor, uid, start_utc_time, end_utc_time)
    clock_time_filter(records)
    return jsonify(records)


@api_bp.route("/usage/cd", methods=["GET"])
def query_cd_special_api_usage():
    """
    Time format "%Y-%m-%d"
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    start_utc_time = request.args.get('start_utc_time')
    end_utc_time = request.args.get('end_utc_time')

    cache_key_format = "{rest_api_id}:{user_id}:{date_id}:cd"

    result = validate_time(start_utc_time, end_utc_time, time_format=DATE_TIME_DAY_FORMAT,
                           validate_func=validate_datetime_format)
    if result['status'] == 'fail':
        return jsonify(result)

    records = query_api_usage(uid, start_utc_time, end_utc_time,
                              time_format=DATE_TIME_DAY_FORMAT,
                              cache_key=cache_key_format)
    clock_time_filter(records)
    return jsonify(records)


@api_bp.route("/usage/da", methods=["GET"])
def query_da_special_api_usage():
    """
    Time format "%Y-%m-%d"
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    start_utc_time = request.args.get('start_utc_time')
    end_utc_time = request.args.get('end_utc_time')

    cache_key_format = "{rest_api_id}:{user_id}:{date_id}:da"

    result = validate_time(start_utc_time, end_utc_time, time_format=DATE_TIME_DAY_FORMAT,
                           validate_func=validate_datetime_format)
    if result['status'] == 'fail':
        return jsonify(result)

    records = query_api_usage(uid, start_utc_time, end_utc_time,
                              time_format=DATE_TIME_DAY_FORMAT,
                              cache_key=cache_key_format)
    clock_time_filter(records)
    return jsonify(records)


@api_bp.route("/usage/ota", methods=["GET"])
def query_ota_special_api_usage():
    """
    Time format "%Y-%m-%d"
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    start_utc_time = request.args.get('start_utc_time')
    end_utc_time = request.args.get('end_utc_time')

    cache_key_format = "{rest_api_id}:{user_id}:{date_id}:ota"

    result = validate_time(start_utc_time, end_utc_time, time_format=DATE_TIME_DAY_FORMAT,
                           validate_func=validate_datetime_format)
    if result['status'] == 'fail':
        return jsonify(result)

    records = query_api_usage(uid, start_utc_time, end_utc_time,
                              time_format=DATE_TIME_DAY_FORMAT,
                              cache_key=cache_key_format)
    clock_time_filter(records)
    return jsonify(records)
