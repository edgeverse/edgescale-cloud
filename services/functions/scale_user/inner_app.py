# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

#! -*- coding: utf-8 -*-
from flask import Flask, request

from model import IS_DEBUG, es_pool, session
from error_handler import handle_dcca_exception
from error_handler import handle_input_exception
from error_handler import handle_other_exception
from edgescale_pyutils.exception_utils import DCCAException, InvalidInputException
from view.users_views import user_bp
from view.account_views import account_bp
from view.users_limit_views import users_limit_bp
from view.user_certificate_views import users_cert_bp
from view.customer_views import custm_bp
from view.vendor_v2_views import vendor_v2_bp


inner_app = Flask(__name__)
inner_app.config["JSON_AS_ASCII"] = False

inner_app.register_blueprint(account_bp, url_prefix="/accounts")
inner_app.register_blueprint(user_bp, url_prefix="/users")
inner_app.register_blueprint(users_cert_bp, url_prefix="/users")
inner_app.register_blueprint(users_limit_bp, url_prefix="/users")
inner_app.register_blueprint(custm_bp, url_prefix="/customers")
inner_app.register_blueprint(vendor_v2_bp, url_prefix="/vendors")

inner_app.register_error_handler(DCCAException, handle_dcca_exception)
inner_app.register_error_handler(InvalidInputException, handle_input_exception)
inner_app.register_error_handler(Exception, handle_other_exception)


@inner_app.before_request
def set_db_conn_and_corsor(*args, **kwargs):
    session.expire_all()
    if not es_pool:
        raise DCCAException("Database Error")
    request.conn = es_pool.connection()
    request.cursor = request.conn.cursor()


@inner_app.teardown_request
def close_db_conn(error):
    if hasattr(request, "conn"):
        request.conn.close()


if __name__ == '__main__':
    inner_app.run(debug=IS_DEBUG, port=5001)
