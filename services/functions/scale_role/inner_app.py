# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Flask, request, jsonify

from model import IS_DEBUG, es_pool, session
from error_handler import handle_dcca_exception
from error_handler import handle_input_exception
from error_handler import handle_other_exception
from utils import DCCAException, InvalidInputException
from view.role_views import role_bp
from view.permission_views import permission_bp
from view.resource_views import resource_bp

inner_app = Flask(__name__)
inner_app.config["JSON_AS_ASCII"] = False


@permission_bp.before_request
def set_db_conn_and_corsor(*args, **kwargs):
    session.expire_all()
    if not es_pool:
        return jsonify({
          "error": True,
          "message": "Database Error",
          "status": "fail"
        })
    request.conn = es_pool.connection()
    request.cursor = request.conn.cursor()


@permission_bp.teardown_request
def close_db_conn(error):
    if hasattr(request, "conn"):
        request.conn.close()


inner_app.register_blueprint(role_bp, url_prefix="/roles")
inner_app.register_blueprint(permission_bp, url_prefix="/permissions")
inner_app.register_blueprint(resource_bp, url_prefix="/resources")

inner_app.register_error_handler(DCCAException, handle_dcca_exception)
inner_app.register_error_handler(InvalidInputException, handle_input_exception)
inner_app.register_error_handler(Exception, handle_other_exception)


if __name__ == '__main__':
    inner_app.run(debug=IS_DEBUG, port=5005)
