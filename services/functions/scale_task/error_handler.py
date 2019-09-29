# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

#! -*- coding: utf-8 -*-
import traceback

from flask import jsonify, request

from model import IS_DEBUG, session


def handle_dcca_exception(e):
    try:
        request.conn.rollback()
    except Exception:
        pass

    try:
        session.rollback()
    except Exception:
        pass

    return jsonify({
        "error": True,
        "status": "fail",
        "message": str(e)
    })


def handle_input_exception(e):
    try:
        request.conn.rollback()
    except Exception:
        pass
    try:
        session.rollback()
    except Exception:
        pass

    return jsonify({
        "error": True,
        "status": "fail",
        "message": str(e)
    })


def handle_other_exception(e):
    if IS_DEBUG:
        traceback.print_exc()

    try:
        request.conn.rollback()
    except Exception:
        pass
    try:
        session.rollback()
    except Exception:
        pass

    data = {
        "error": True,
        "tatus": "fail",
        "message": "Fail to execute lambda."
    }

    if IS_DEBUG:
        data['debug'] = str(e)
    return jsonify(data)
