# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

def handle(event, context):
    return {
        "statusCode": 200,
        "body": "Hello from OpenFaaS!"
    }
