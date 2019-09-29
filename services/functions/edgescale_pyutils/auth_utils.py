# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import hashlib
import random
import string
from binascii import a2b_hex
from datetime import datetime, timedelta

import jwt
from Crypto.Cipher import AES
from binascii import b2a_hex

from edgescale_pymodels.constants import USER_TOKEN_KEY, TIME_FORMAT_STR, MAIL_TOKEN_KEY
from edgescale_pymodels.constants import ADMIN_FLAG


class DCCACrypt(object):
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        length = 16
        count = len(text)
        add = length - (count % length)
        text = text + ('\0' * add)
        ciphertext = cryptor.encrypt(text)

        return b2a_hex(ciphertext)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        plain_text = cryptor.decrypt(a2b_hex(text))
        return plain_text.decode().rstrip('\0')


def encrypt_with_random_salt(password: string) -> (string, string):
    salt = ''.join([(string.ascii_letters + string.digits)[x] for x in random.sample(list(range(0, 62)), 32)])
    return encrypt_with_salt(password, salt), salt


def encrypt_with_salt(password: string, salt: string) -> string:
    x = hashlib.md5()
    x.update(password.encode())
    x.update(salt.encode())
    return x.hexdigest()


def make_token(user, delta_hours=24) -> string:
    is_admin = ADMIN_FLAG if user.admin else 0
    data = {
        'exp': datetime.utcnow() + timedelta(hours=delta_hours),
        'uid': user.uid,
        'username': user.username,
        'admin': is_admin,
        'account_type_id': user.account_type_id
    }

    token = jwt.encode(data, USER_TOKEN_KEY)
    return token.decode()


def generate_token(user_id) -> string:
    time_str = datetime.strftime(datetime.now(), TIME_FORMAT_STR)

    crypter = DCCACrypt(MAIL_TOKEN_KEY)
    token = crypter.encrypt(str(user_id) + ' ' + time_str)

    return token.decode()
