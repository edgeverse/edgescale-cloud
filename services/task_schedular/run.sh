#! /bin/sh
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

while true
do
 python3 task_schedular.py 
 sleep 5
 python3 task_updater.py
 sleep 5
done

