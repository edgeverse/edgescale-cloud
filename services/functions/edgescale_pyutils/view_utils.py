# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import boto3
from botocore.exceptions import ClientError

from edgescale_pymodels.constants import DEFAULT_MAIL_TOKEN_TIMEOUT_STR, body_html_rest_password
from email.mime.text import MIMEText
from email.header import Header
import smtplib


def get_oemid(request):
    uid = request.headers.get("uid")
    if uid is not None:
        return uid, None

    uid = request.headers.get("user_id")
    if uid is not None:
        return uid, None

    return -1, Exception("unAuth")


def get_json(request):
    return request.json or {}


def send_email(SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PASSWD, recipient, subject_html, body_html):
    SENDER = ADMIN_EMAIL
    # The email body for recipients with non-HTML email clients.
    SUBJECT = subject_html
    CHARSET = "UTF-8"
    msg = MIMEText(body_html, "html", CHARSET)
    msg["Subject"] = SUBJECT
    msg["From"] = ADMIN_EMAIL
    msg["To"] = recipient
    try:
        server = smtplib.SMTP(SMTP_HOST, str(SMTP_PORT))
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(ADMIN_EMAIL, ADMIN_EMAIL_PASSWD)
        server.sendmail(ADMIN_EMAIL, recipient, msg.as_string())
        server.quit()
    # Display an error if something goes wrong.
    except ClientError as e:
        return {
            'status': 'fail',
            'message': 'Fail to send email, contact the administrator.',
            'e': str(e)
        }
    else:
        return {
            'status': 'success',
            'message': 'An email has been sent',
        }


def send_email_reset_pwd(SMTP_HOST, SMTP_PORT, ADMIN_EMAIL, ADMIN_EMAIL_PASSWD, recipient, token, account, host):
    SUBJECT = "Reset your password"
    BODY_HTML = body_html_rest_password.format(account=account, token=token, time=DEFAULT_MAIL_TOKEN_TIMEOUT_STR,
                                               host=host)

    # The character encoding for the email.
    CHARSET = "UTF-8"
    msg = MIMEText(BODY_HTML, "html", CHARSET)
    msg["Subject"] = SUBJECT
    msg["From"] = ADMIN_EMAIL
    msg["To"] = recipient
    try:
        server = smtplib.SMTP(SMTP_HOST, str(SMTP_PORT))
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(ADMIN_EMAIL, ADMIN_EMAIL_PASSWD)
        server.sendmail(ADMIN_EMAIL, recipient, msg.as_string())
        server.quit()
    except Exception as e:
        return {
            'status': 'fail',
            'message': 'Fail to send email, contact the administrator.',
            'e': str(e)
        }
    else:
        return {
            'status': 'success',
            'message': 'An email has been sent, reset your password in {}'.format(DEFAULT_MAIL_TOKEN_TIMEOUT_STR),
        }


def account_str(username, email):
    return "username: {}<br>email: {}".format(username, email)
