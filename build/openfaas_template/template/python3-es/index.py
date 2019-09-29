# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import json
import sys
sys.path.append("./function")

from io import BytesIO
from base64 import b64decode
from urllib.parse import urlencode

from bottle import Bottle, request, HTTPResponse

from inner_app import inner_app


handler_app = Bottle()
wsgi_app = inner_app
BINARY_SUPPORT = False


def get_environ(event, binary_support):
    method = event.get("httpMethod", "GET")
    body = event.get("body", "") or ""
    params = event.get("queryStringParameters") or {}
    path = event.get("path", "")

    environ = {
        "CONTENT_LENGTH": str(len(body)),
        "HTTP": "on",
        "PATH_INFO": path,
        "QUERY_STRING": urlencode(params),
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.errors": sys.stderr,
        "wsgi.input": BytesIO(body.encode("utf-8")),
        "wsgi.multiprocess": False,
        "wsgi.multithread": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "5000"
    }

    # set auth
    authorizer = event.get("authorizer", {})
    uid = authorizer.get("principalId", "")
    admin = authorizer.get("admin", "false")
    environ["HTTP_UID"] = str(uid)
    environ["HTTP_ADMIN"] = str(admin).lower()
    environ["HTTP_HOST"] = "127.0.0.1"
    environ["CONTENT_TYPE"] = "application/json" if method.upper() in ["POST", "PUT", "PATCH", "DELETE"] and body else "text/html; charset=utf-8"

    headers = event.get('headers') or {}  # may be None when testing on console
    for key, value in headers.items():
        key = key.upper().replace("-", "_")

        if key == "CONTENT_TYPE":
            continue

        environ["HTTP_" + key] = value

    # Pass the AWS requestContext to the application
    if "requestContext" in event:
        environ["apig_wsgi.request_context"] = event["requestContext"]

    return environ


class MResponse(object):
    def __init__(self, binary_support):
        self.status_code = 500
        self.headers = []
        self.body = BytesIO()
        self.binary_support = binary_support

    def start_response(self, status, response_headers, exc_info=None):
        # Handling exceptions
        if exc_info is not None:
            raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])

        self.status_code = int(status.split()[0])
        if self.headers:
            raise AssertionError("Headers already set")
        self.headers[:] = response_headers
        return self.body.write

    def consume(self, application_iter):
        try:
            for data in application_iter:
                if data:
                    self.body.write(data)
        finally:
            if hasattr(application_iter, "close"):
                application_iter.close()

    def as_kong_response(self):
        return self.body.getvalue().decode("utf-8")

    def get_header(self):
        return {k: v for k, v in self.headers}


def make_err_response(code, message):
    body = json.dumps({
        "error": True,
        "status": "failed",
        "message": message
    })
    return body


@handler_app.route("/<path:path>", method="POST")
@handler_app.route("/", method="POST")
def index(path=""):
    event = {}
    data = request.body.read()
    try:
        event = json.loads(data)
    except Exception:
        message = "Body must be a serialized json string." 
        return HTTPResponse(make_err_response(500, message), status=200, headers={"Content-Type": "application/json"})

    environ = get_environ(event, binary_support=BINARY_SUPPORT)
    response = MResponse(binary_support=BINARY_SUPPORT)
    application_iter = wsgi_app(environ, response.start_response)
    response.consume(application_iter)
    return HTTPResponse(response.as_kong_response(), response.status_code, response.get_header())


if __name__ == "__main__":
    handler_app.run(debug=True, port=5000)
