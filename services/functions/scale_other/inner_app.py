# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from flask import Flask, request

from error_handler import handle_dcca_exception, handle_input_exception, handle_other_exception
from edgescale_pyutils.exception_utils import DCCAException, InvalidInputException, InvalidParameterException
from model import IS_DEBUG, es_pool
from view.api_views import api_bp
from view.deployment_views import deployment_bp
from view.info_views import info_bp
from view.model_views import model_bp
from view.registry_views import registry_bp
from view.service_views import service_bp
from view.storage_views import storage_bp
from view.audit_views import audit_bp


inner_app = Flask(__name__)
inner_app.config["JSON_AS_ASCII"] = False

inner_app.register_blueprint(api_bp, url_prefix="/api")
inner_app.register_blueprint(deployment_bp, url_prefix="/deployment")
inner_app.register_blueprint(info_bp, url_prefix="/info")
inner_app.register_blueprint(model_bp, url_prefix="/models")
inner_app.register_blueprint(registry_bp, url_prefix="/registry")
inner_app.register_blueprint(service_bp, url_prefix="/services")
inner_app.register_blueprint(storage_bp, url_prefix="/storage")
inner_app.register_blueprint(audit_bp, url_prefix="/audit")

inner_app.register_error_handler(DCCAException, handle_dcca_exception)
inner_app.register_error_handler(InvalidInputException, handle_input_exception)
inner_app.register_error_handler(InvalidParameterException, handle_input_exception)
inner_app.register_error_handler(Exception, handle_other_exception)


@inner_app.before_request
def set_db_conn_and_corsor(*args, **kwargs):
    if not es_pool:
        raise DCCAException("Database Error")
    request.conn = es_pool.connection()
    request.cursor = request.conn.cursor()


@inner_app.teardown_request
def close_db_conn(error):
    if hasattr(request, "conn"):
        request.conn.close()


if __name__ == '__main__':
    inner_app.run(debug=IS_DEBUG, port=5008)
