# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP



class DCCAException(Exception):
    pass


class ReqContext(object):
    current_user = None


ctx = ReqContext()


class InvalidInputException(Exception):
    pass


def empty_check(value, error_message):
    if not value:
        raise InvalidInputException(error_message)


def empty_check_chian(value, error_message, errors=None):
    if errors is None:
        errors = []

    if not value:
        errors.append(error_message)
    return errors
