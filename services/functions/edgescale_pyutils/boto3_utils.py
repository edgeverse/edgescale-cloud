# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import boto3

from edgescale_pymodels.constants import IMAGE_BUCKET


def s3_folder_exists(username):
    client = boto3.client('s3')
    o = client.list_objects(Bucket=IMAGE_BUCKET, Prefix=username + '/')
    if 'Contents' in o:
        return True
    else:
        return False


def create_foler(username):
    resource = boto3.resource('s3')
    bucket = resource.Bucket(IMAGE_BUCKET)
    bucket.put_object(Key=username + '/')


def remove_image_from_s3(bucket, key_s3):
    s3 = boto3.client('s3')
    s3.delete_object(Bucket=bucket, Key=key_s3)
