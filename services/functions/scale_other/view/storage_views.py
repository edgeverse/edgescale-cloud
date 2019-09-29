# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Blueprint, request, jsonify

from model.constants import *
from utils import *


storage_bp = Blueprint("storage", __name__)


@storage_bp.route("/signer", methods=["GET"])
def get_url():
    key = request.args.get('key')
    file_type = request.args.get('type')

    if file_type in bucket_list:
        result = get_presigned_url(bucket_list[file_type], key)
    else:
        result = "type error!"

    return jsonify(result)
