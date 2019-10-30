#!/bin/bash
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

filepath=$(cd "$(dirname "$0")"; pwd)
basepath=${filepath%/*}

kubernetes_ver=1.15.0
docker_ver=18.09.0
faas_ver=0.8.0

ethname=$(ip -o -4 route show to default | awk '{print $5}' | head -1)
LocalIP=$(ip -o -4 addr list $ethname | awk '{print $4}' | cut -d/ -f1 | head -1)
ConfigPath=($basepath/install/kubernetes/config/vars.json)
# install json tool
if [ ! `command -v jq` ];then
    apt install -y jq
fi

FAAS_PASSWORD=$(cat $ConfigPath | jq -r '.env.faas_passwd')
FAAS_USER=$(cat $ConfigPath | jq -r '.env.faas_user')

POSTGRES_PASSWD=$(cat $ConfigPath | jq -r '.db.pg_passwd')
POSTGRES_ES_PASSWD=$(cat $ConfigPath | jq -r '.db.pg_es_passwd')
POSTGRES_KONG_PASSWD=$(cat $ConfigPath | jq -r '.db.kong_passwd')
POSTGRES_MAX_CONNECTION=$(cat $ConfigPath | jq -r '.db.pg_max_connections')
REDIS_PASSWORD=$(cat $ConfigPath | jq -r '.service.REDIS_PASSWD' )

MINIO_ACCESS_KEY=$(cat $ConfigPath | jq -r '.minio.access_key')
MINIO_SECRET_KEY=$(cat $ConfigPath | jq -r '.minio.secret_key')

HARBOR_IP_ADDRESS=$(cat $ConfigPath | jq -r '.env.harbor_host_ip')
HARBOR_DOMAIN=$(cat $ConfigPath | jq -r '.env.harbor_domain')
HARBOR_REPO_SUB_DIR=$(cat $ConfigPath | jq -r '.env.harbor_project_name')
HARBOR_PASSWORD=$(cat $ConfigPath | jq -r '.env.harbor_passwd')
HARBOR_USER=$(cat $ConfigPath | jq -r '.env.harbor_user')

DOMAIN_NAME=$(cat $ConfigPath | jq -r '.env.domain_name')
SSL_CERT=$(cat $ConfigPath | jq -r '.ssl.cert_path')
SSL_KEY=$(cat $ConfigPath | jq -r '.ssl.key_path')

set +e
set -o noglob

#
# Set Colors
#

bold=$(tput bold)
underline=$(tput sgr 0 1)
reset=$(tput sgr0)

red=$(tput setaf 1)
green=$(tput setaf 76)
white=$(tput setaf 7)
tan=$(tput setaf 202)
blue=$(tput setaf 25)

#
# Headers and Logging
#

underline() { printf "${underline}${bold}%s${reset}\n" "$@"
}
h1() { printf "\n${underline}${bold}${blue}%s${reset}\n" "$@"
}
h2() { printf "\n${underline}${bold}${white}%s${reset}\n" "$@"
}
debug() { printf "${white}%s${reset}\n" "$@"
}
info() { printf "${white}➜ %s${reset}\n" "$@"
}
success() { printf "${green}✔ %s${reset}\n" "$@"
}
error() { printf "${red}✖ %s${reset}\n" "$@"
}
warn() { printf "${tan}➜ %s${reset}\n" "$@"
}
bold() { printf "${bold}%s${reset}\n" "$@"
}
note() { printf "\n${underline}${bold}${blue}Note:${reset} ${blue}%s${reset}\n" "$@"
}

set -e
set +o noglob

function Check_sw_ver() {
    sleep 1
    if ! $check_sw $check_arg &> /dev/null
    then
        error "Need to install $check_sw($except_version_part1.$except_version_part2.$except_version_part3) first and run this script again."
        exit 1
    fi
    
    if [[ $($check_sw $check_arg) =~ (([0-9]+).([0-9]+).([0-9]+)) ]]
    then
        version=${BASH_REMATCH[1]}
        version_part1=${BASH_REMATCH[2]}
        version_part2=${BASH_REMATCH[3]}
        
        if [ "$version_part1" -lt $except_version_part1 ] || ([ "$version_part1" -eq $except_version_part1 ] && [ "$version_part2" -lt $except_version_part2 ])
        then
            error "Need to upgrade $check_sw package to $except_version_part1.$except_version_part2.$except_version_part3 ."
            exit 1
        else
            note "$check_sw version: $version"
        fi
    else
        error "Failed to parse $check_sw version."
        exit 1
    fi
}

function Check_k8s_ver(){
    except_version_part1="18"
    except_version_part2="09"
    except_version_part3="0+"
    check_sw="docker"
    check_arg="version"
    Check_sw_ver

    except_version_part1="1"
    except_version_part2="15"
    except_version_part3="0+"
    
    check_sw="kubeadm"
    check_arg="version"
    Check_sw_ver

    check_sw="kubectl"
    check_arg="version --client"
    Check_sw_ver

    check_sw="kubelet"
    check_arg="--version"
    Check_sw_ver

    except_version_part1="0"
    except_version_part2="8"
    except_version_part3="0+"
    check_sw="faas-cli"
    check_arg="version --short-version"
    Check_sw_ver
}

function Login_harbor(){
    if [ -z `grep $HARBOR_DOMAIN /etc/hosts|awk {'print $2'}` ]
    then
    sed -i '$a '$HARBOR_IP_ADDRESS' '$HARBOR_DOMAIN'' /etc/hosts
    fi
    kubectl create secret docker-registry kube-repos --docker-server=$HARBOR_DOMAIN --docker-username=$HARBOR_USER --docker-password=$HARBOR_PASSWORD --namespace openfaas-util
    kubectl create secret docker-registry faas-repos --docker-server=$HARBOR_DOMAIN --docker-username=$HARBOR_USER --docker-password=$HARBOR_PASSWORD --namespace openfaas-fn
}


function CMD() {
    echo "CMD: $@"
    $@
   # if [$? -ne 0];then
   #     exit 1
   # fi
   echo "****************end*******************"
}


pod_name=kube-apiserver
function Wait_pod_running(){
    sleep 1
    while [ -z `kubectl get pods --all-namespaces | grep $pod_name | awk {'print $4'}` ]
    do
        sleep 1
    done

    sleep 1
    while [ -n `kubectl get pods --all-namespaces | grep $pod_name | awk {'print $4'}` ]
    do
        sleep 1
        if [ `kubectl get pods --all-namespaces | grep $pod_name | awk {'print $4'}` == Running ]
        then
            break 1
        fi
    done
    echo "OPENFAAS $pod_name running."
    sleep 1
}

pod_ready=1/1
function Wait_pod_ready(){
    sleep 1
    while [ -z `kubectl get pods --all-namespaces | grep $pod_name | awk {'print $3'}` ]
    do
        sleep 1
    done

    sleep 1
    while [ -n `kubectl get pods --all-namespaces | grep $pod_name | awk {'print $3'}` ]
    do
        sleep 1
        if [ `kubectl get pods --all-namespaces | grep $pod_name | awk {'print $3'}` == $pod_ready ]
        then
            break 1
        fi
    done
    echo "OPENFAAS $pod_name ready."
    sleep 1
}

function Reset_k8s_system(){
    kubeadm reset -f
    systemctl stop kubelet
    systemctl stop docker
    rm -rf /var/lib/cni/
    rm -rf /var/lib/etcd
    rm -rf /var/lib/kubelet/*
    rm -rf /etc/cni/

    if ifconfig cni0 &> /dev/null
    then
        ifconfig cni0 down
    fi

    if ifconfig flannel.1 &> /dev/null
    then
        ifconfig flannel.1 down
    fi

    if ifconfig docker0 &> /dev/null
    then
        ifconfig docker0 down
    fi

    if ip link cni0 &> /dev/null
    then
        ip link delete cni0
    fi

    if ip link flannel.1 &> /dev/null
    then
        ip link delete flannel.1
    fi
    
    systemctl restart kubelet
    systemctl restart docker
}

function Start_k8s_system(){
    swapoff -a
    cp -p /etc/fstab /etc/fstab.bak$(date '+%Y%m%d%H%M%S')
    # for ubuntu modify the fstab file
    sed -i "s/^\/swapfile/\#\/swapfile/g" /etc/fstab 
    kubeadm init --pod-network-cidr=10.244.0.0/16        
    mkdir -p $HOME/.kube
    cp /etc/kubernetes/admin.conf $HOME/.kube/config
    chown $(id -u):$(id -g) $HOME/.kube/config
    
    kubectl apply -f $basepath/install/kubernetes/kube-flannel.yml

    kubectl apply -f $basepath/install/kubernetes/namespaces.yml
    kubectl get ns -A
    
    #By default, your cluster will not schedule pods on the master for security reasons. If you want to be able to schedule 
    #pods on the master, e.g. for a single-machine Kubernetes cluster for development, run:
    kubectl taint nodes --all node-role.kubernetes.io/master-
}

function Start_faas_netes(){
    kubectl -n openfaas create secret generic basic-auth --from-literal=basic-auth-user=$FAAS_USER --from-literal=basic-auth-password="$FAAS_PASSWORD" 
    kubectl apply -f $basepath/install/kubernetes/kube_openfaas_yaml
    kubectl expose service prometheus  --port=9090 --target-port=9090  --name=prometheus-service --external-ip=$LocalIP --namespace=openfaas
    kubectl expose service alertmanager  --port=9094 --target-port=9094  --name=alertmanager-service --external-ip=$LocalIP --namespace=openfaas

}

function Set_harborinfo_into_yaml(){
    file_list=$(find $basepath/install/kubernetes/ -name *.template)

    for f in $file_list
    do
        new_file=$(echo ${f%*.template})
        
    	cp $f $new_file
    	sed -i "s/HARBOR_URL\/HARBOR_REPO_SUB_DIR/$HARBOR_DOMAIN\/$HARBOR_REPO_SUB_DIR/g" $new_file
    done

}

function Prepare_edgescale_env(){
    Set_harborinfo_into_yaml

    mkdir -p /etc/edgescale/etc/b-est/ca
    cp $basepath/install/kubernetes/j2_conf/b-est.conf.j2 /etc/edgescale/etc/b-est/config.yaml
    cp $basepath/install/kubernetes/j2_conf/b-est-rootca.crt.j2 /etc/edgescale/etc/b-est/ca/RootCA.crt
    cp $basepath/install/kubernetes/j2_conf/b-est-rootca.key.j2 /etc/edgescale/etc/b-est/ca/RootCA.key
    cp $basepath/install/kubernetes/j2_conf/b-est.crt.j2 /etc/edgescale/etc/b-est/est.crt
    cp $basepath/install/kubernetes/j2_conf/b-est.key.j2 /etc/edgescale/etc/b-est/est.key
    cp $basepath/install/kubernetes/j2_conf/b-est.trust.crt.j2 /etc/edgescale/etc/b-est/trustca.crt

    mkdir -p /etc/edgescale/etc/e-est/ca
    cp $basepath/install/kubernetes/j2_conf/e-est.conf.j2 /etc/edgescale/etc/e-est/config.yaml
    cp $basepath/install/kubernetes/j2_conf/e-est-rootca.crt.j2 /etc/edgescale/etc/e-est/ca/RootCA.crt
    cp $basepath/install/kubernetes/j2_conf/e-est-rootca.key.j2 /etc/edgescale/etc/e-est/ca/RootCA.key
    cp $basepath/install/kubernetes/j2_conf/e-est.crt.j2 /etc/edgescale/etc/e-est/est.crt
    cp $basepath/install/kubernetes/j2_conf/e-est.key.j2 /etc/edgescale/etc/e-est/est.key
    cp $basepath/install/kubernetes/j2_conf/e-est.trust.crt.j2 /etc/edgescale/etc/e-est/trustca.crt

    mkdir -p /etc/edgescale/etc/emqttd/certs
    cp $basepath/install/kubernetes/j2_conf/emq.conf.j2 /etc/edgescale/etc/emqttd/emq.conf
    cp $basepath/install/kubernetes/j2_conf/emq_ssl.conf.j2 /etc/edgescale/etc/emqttd/ssl_dist.conf
    cp $basepath/install/kubernetes/j2_conf/emq_acl.conf.j2 /etc/edgescale/etc/emqttd/acl.conf
    cp $basepath/install/kubernetes/j2_conf/emq_cert.j2 /etc/edgescale/etc/emqttd/certs/cert.pem
    cp $basepath/install/kubernetes/j2_conf/emq_key.j2 /etc/edgescale/etc/emqttd/certs/key.pem

    mkdir -p /etc/edgescale/etc/haproxy/log
    cp $basepath/install/kubernetes/j2_conf/haproxy.conf.j2 /etc/edgescale/etc/haproxy/haproxy.cfg
    sed -i "s/{{ master_ip }}/$LocalIP/g" /etc/edgescale/etc/haproxy/haproxy.cfg
    #change the domain_name
    sed -i "s/{{ domain_name }}/$DOMAIN_NAME/g" /etc/edgescale/etc/haproxy/haproxy.cfg

    mkdir -p /etc/edgescale/etc/named
    cp $basepath/install/kubernetes/j2_conf/named.conf.j2 /etc/edgescale/etc/named/named.conf
    cp $basepath/install/kubernetes/j2_conf/named.edgescale.zone.j2 /etc/edgescale/etc/named/edgescale.zone
    sed -i "s/{{master_ip}}/$LocalIP/g" /etc/edgescale/etc/named/named.conf
    sed -i "s/{{ domain_name }}/$DOMAIN_NAME/g" /etc/edgescale/etc/named/named.conf
    sed -i "s/{{ master_ip }}/$LocalIP/g" /etc/edgescale/etc/named/edgescale.zone
    sed -i "s/{{ domain_name }}/$DOMAIN_NAME/g" /etc/edgescale/etc/named/edgescale.zone

    mkdir -p /var/edgescale/nginx/www
    mkdir -p /etc/edgescale/etc/nginx/ssl
    cp $basepath/install/kubernetes/j2_conf/nginx.conf.j2 /etc/edgescale/etc/nginx/nginx.conf
    sed -i "s/{{ domain_name }}/$DOMAIN_NAME/g" /etc/edgescale/etc/nginx/nginx.conf
    cp $basepath$SSL_CERT /etc/edgescale/etc/nginx/ssl/edgescale.crt
    cp $basepath$SSL_KEY /etc/edgescale/etc/nginx/ssl/edgescale.key
    cp $basepath/install/kubernetes/resource/dashboard.zip /tmp/dashboard.zip
    if ! unzip -n /tmp/dashboard.zip -d /var/edgescale/nginx/www &> /dev/null
    then
        error "unzip dashboard.zip failed!"
        exit 1
    fi

    mkdir -p /etc/edgescale/etc/redis/
    cp $basepath/install/kubernetes/j2_conf/redis.conf.j2 /etc/edgescale/etc/redis/redis.conf
    sed -i "s/{{ db.redis_pass }}/$REDIS_PASSWORD/g" /etc/edgescale/etc/redis/redis.conf

    sed -i "s/postgres_password/$POSTGRES_PASSWD/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-1/redis.yaml
    sed -i "s/postgres_password/$POSTGRES_PASSWD/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-1/postgres.yaml
    sed -i "s/kong_password/$POSTGRES_KONG_PASSWD/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-1/postgres.yaml

    sed -i "s/access_key/$MINIO_ACCESS_KEY/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio.yaml
    sed -i "s/secret_key/$MINIO_SECRET_KEY/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio.yaml
    sed -i "s/HARBOR_URL\/HARBOR_REPO_SUB_DIR/$HARBOR_DOMAIN\/$HARBOR_REPO_SUB_DIR/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio.yaml

    sed -i "s/access_key/$MINIO_ACCESS_KEY/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio-api.yaml
    sed -i "s/secret_key/$MINIO_SECRET_KEY/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio-api.yaml
    sed -i "s/minio_ip/$LocalIP/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio-api.yaml
    sed -i "s/HARBOR_URL\/HARBOR_REPO_SUB_DIR/$HARBOR_DOMAIN\/$HARBOR_REPO_SUB_DIR/g" $basepath/install/kubernetes/kube_edgescale_yaml/phase-2/minio-api.yaml
    cp $basepath/install/kubernetes/resource/*.dump /etc/edgescale/
    rm -rf /var/edgescale/postgresql/data/

}

function Start_edgescale_inbox(){
    rm -rf /etc/edgescale/kong
    cp -r $basepath/kong /etc/edgescale/
    cp -r $basepath$SSL_CERT /etc/edgescale/kong 
    cp -r $basepath$SSL_KEY /etc/edgescale/kong 
}

function Start_edgescale(){

    kubectl apply -f $basepath/install/kubernetes/kube_edgescale_yaml/phase-1

    pod_name=postgres
    Wait_pod_running

    pod_ready=1/1
    Wait_pod_ready

    POSTGRES_CONTAINER=`docker ps |grep postgres | grep -v pause | awk {'print $1'}`

    if ! docker exec $POSTGRES_CONTAINER  env PGPASSWORD=$POSTGRES_PASSWD psql  -U postgres -c "CREATE USER root WITH PASSWORD '$POSTGRES_ES_PASSWD'" &> /dev/null
    then
        error "postgres create user root failed!"
        exit 1
    fi

    if ! docker exec $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD psql  -U postgres -c "create database edgescale_mft" &> /dev/null
    then
        error "postgres create database edgescale_mft failed!"
        exit 1
    fi

    if ! docker exec -i $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD psql  -U postgres -d edgescale_mft < /etc/edgescale/edgescale_mft.dump &> /dev/null
    then
        error "postgres inject database edgescale_mft failed!"
        exit 1
    fi
    
    if ! docker exec $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD psql  -U postgres -c "create database edgescale" &> /dev/null
    then
        error "postgres create database edgescale failed!"
        exit 1
    fi

    if ! docker exec -i $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD psql  -U postgres -d edgescale < /etc/edgescale/edgescale_init.dump &> /dev/null
    then
        error "postgres inject database edgescale_init failed!"
        exit 1
    fi
    

    if ! docker exec $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD  psql -U postgres -c "CREATE USER kong WITH PASSWORD '$POSTGRES_KONG_PASSWD'" &> /dev/null
    then
        error "postgres create user kong failed!"
        exit 1
    fi

    if ! docker exec $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD psql  -U postgres -c "create database kong" &> /dev/null
    then
        error "postgres create database kong failed!"
        exit 1
    fi

    if ! docker exec -i $POSTGRES_CONTAINER env PGPASSWORD=$POSTGRES_PASSWD psql -U postgres -d kong < /etc/edgescale/kong.dump &> /dev/null
    then
        error "postgres inject database kong failed!"
        exit 1
    fi
    

    sed -i /max_connections/d /var/edgescale/postgresql/data/postgresql.conf
    sed -i '$a max_connections = '$POSTGRES_MAX_CONNECTION'' /var/edgescale/postgresql/data/postgresql.conf
    kubectl delete pods -n openfaas-util `kubectl get pods -A |grep postgres | awk '{print $2}'`

    pod_name=postgres
    Wait_pod_running

    kubectl apply -f $basepath/install/kubernetes/kube_edgescale_yaml/phase-2

    pod_name=minio
    Wait_pod_running

    pod_name=haproxy
    Wait_pod_running

    kubectl expose service emqtt-external --port=1883 --target-port=1883  --name=emqtt-service1 --external-ip=$LocalIP --namespace=openfaas-util
    kubectl expose service emqtt-external --port=8883 --target-port=8883  --name=emqtt-service2 --external-ip=$LocalIP --namespace=openfaas-util
    kubectl expose service minio-external --port=9000 --target-port=9000  --name=minio-service --external-ip=$LocalIP --namespace=openfaas-util
    kubectl expose service minio-api-external --port=10086 --target-port=10086  --name=minio-api-service --external-ip=$LocalIP --namespace=openfaas-util
    kubectl expose service postgres-external --port=5432 --target-port=5432 --name=postgres-service --external-ip=$LocalIP --namespace=openfaas-util 
    kubectl expose service app-orch-svr-external --port=7443 --target-port=7443  --name=app-orch-svr-service --external-ip=$LocalIP --namespace=openfaas-util
    
}


function Modify_config(){
    if [ ! `command -v pip3` ];then
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py
        rm get-pip.py
    fi
    cd $basepath/install/kubernetes/config
    pip3 install -r requirements.txt
    python3 config.py
}


function Start_scale_function(){
    kubectl delete pods -n openfaas-util `kubectl get pods -A |grep kong | awk '{print $2}'`
    pod_name=kong 
    Wait_pod_running 

    cd $basepath/build/openfaas_template
    python gen_yaml.py

    pod_name=gateway
    Wait_pod_running

    pod_name=faas-idler
    Wait_pod_running
    

    export OPENFAAS_URL=http://127.0.0.1:31112
    cd $basepath/build/openfaas_template
    faas-cli login -u $FAAS_USER -p $FAAS_PASSWORD 
    for f in `ls *.yml`
        do
            faas-cli deploy -f $f
        done
    rm $basepath/build/openfaas_template/*.yml

    pod_name=scale-user
    Wait_pod_running
    pod_name=scale-task
    Wait_pod_running
}

Check_k8s_ver
Reset_k8s_system
Start_k8s_system
Start_faas_netes
Login_harbor
Prepare_edgescale_env
Start_edgescale_inbox
Start_edgescale
Modify_config 
Start_scale_function

