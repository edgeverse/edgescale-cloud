#bin/bash
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

harbor_domain_name="docker.edgescale.demo" 
basepath=$(cd "$(dirname "$0")"; pwd)


function DeployHarbor(){
    res=`which docker-compose`
    if [ "$res" != "" ];then
            echo "docker-compose have been install."
    else
            curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            echo "docker-compose install complete"
    fi
    wget https://storage.googleapis.com/harbor-releases/release-1.7.0/harbor-offline-installer-v1.7.5.tgz
    tar -zxvf harbor-offline-installer-v1.7.5.tgz 
    sed -i "8s/reg.mydomain.com/$harbor_domain_name/g" $basepath/harbor/harbor.cfg
    sed -i "12s/http/https/g" $basepath/harbor/harbor.cfg
    sed -i "206s/redis/redis_harbor/g" $basepath/harbor/docker-compose.yml
    sed -i "228s/nginx/nginx_harbor/g" $basepath/harbor/docker-compose.yml 
    sed -i "244s/^443/441/g" $basepath/harbor/docker-compose.yml 
    sed -i "245s/^4443/8441/g" $basepath/harbor/docker-compose.yml 
    sudo mkdir -p /data/cert
    sudo cp $basepath/harbor_cert/* /data/cert/
    sudo $basepath/harbor/install.sh 
    sudo rm -rf harbor *.tgz
    sudo rm -rf /data/cert
}

DeployHarbor

