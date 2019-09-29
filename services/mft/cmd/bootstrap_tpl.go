// SPDX-License-Identifier: Apache-2.0 OR MIT
// Copyright 2018-2019 NXP

package main

var bootstrapEnrollTpl = `
#!/bin/bash

DiskInfo=$(fdisk -l $1 2>&1|grep "Disk /dev")
if [ $? -ne 0 ]||[ $# -eq 0 ]
then
        echo "usage: sudo $0 /dev/<sdx>"
        exit 1
fi


echo Install Edgescale AAA service Private key to $DiskInfo
echo "--- Yes|No ---"

read install

if [ $install = "Yes" ] || [ $install = "yes" ]
then
        dd if=/dev/zero of=secure.bin bs=1M count=1 > /dev/null
        mke2fs secure.bin
        mkdir -p /tmp/secure
        mount -o loop secure.bin /tmp/secure
        mkdir -p /tmp/secure/certs
        mkdir -p /tmp/secure/private_keys

        cat > /tmp/secure/private_keys/mf-private.pem << EOF
{{.DeviceKey}}
EOF

        echo  {{.DeviceID}} >> /tmp/secure/device-id.ini
        sync
        umount /tmp/secure
        dd if=secure.bin of=$1 seek=62 bs=1M
    dd if=/dev/zero of=$1 seek=63 bs=1M count=1
        sync
        rm -r secure.bin /tmp/secure
else
        echo bye
        exit 1
fi`

var bootstrapEnrollSecureTpl = `
#!/bin/bash

DiskInfo=$(fdisk -l $1 2>&1|grep "Disk /dev")
if [ $? -ne 0 ]||[ $# -eq 0 ]
then
        echo "usage: sudo $0 /dev/<sdx>"
        exit 1
fi


echo Erase $1 edgescale private keys: $DiskInfo
echo "--- Yes|No ---"

if [ $install = "Yes" ] || [ $install = "yes" ]
then
    dd if=/dev/zero of=$1 seek=62 bs=1M count=2
else
        echo bye
        exit 1
fi`
