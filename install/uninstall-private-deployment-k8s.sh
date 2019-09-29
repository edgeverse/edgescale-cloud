#!/bin/bash
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

filepath=$(cd "$(dirname "$0")"; pwd)
basepath=${filepath%/*}

HARBOR_DOMAIN=$(cat $basepath/install/kubernetes/config/vars.json | jq -r '.env.harbor_domain')

if [ -n `grep $HARBOR_DOMAIN /etc/hosts|awk {'print $2'}` ]
then
    sed -i '/'$HARBOR_DOMAIN'/d' /etc/hosts
fi

function Reset_k8s_system(){
    kubeadm reset -f
    systemctl stop kubelet
    systemctl stop docker
    rm -rf /var/lib/cni/
    rm -rf /var/lib/etcd
    rm -rf /var/lib/kubelet/*
    rm -rf /etc/cni/
    ifconfig cni0 down
    ifconfig flannel.1 down
    ifconfig docker0 down
    ip link delete cni0
    ip link delete flannel.1
    systemctl restart kubelet
    systemctl restart docker
}

function Remove_dir(){
   rm -rf $HOME/.kube
   rm -rf /etc/edgescale
   rm -rf /var/edgescale
}

function Remove_function_images(){
    cd $basepath/build/openfaas_template
    python gen_yaml.py

    for f in `ls *.yml`
        do
            image_list=$(grep 'image:' $f|awk {'print $2'}|cut -d ":" -f 1)
            for img in $image_list
            do
                image_exist=$(docker image ls |grep $img)
                if [ "$image_exist" ]
                then
                    docker image ls -q $img |  xargs docker image rm -f
                fi
            done
        done

    rm $basepath/build/openfaas_template/*.yml
}

function Remove_edgescale_images(){
    file_list=$(grep -r 'image:' $basepath/install/kubernetes/kube_edgescale_yaml|grep -v '.template'|awk {'print $1'}|cut -d ":" -f 1)
    for f in $file_list
        do
            image_list=$(grep 'image:' $f|awk {'print $2'}|cut -d ":" -f 1)
            for img in $image_list
            do
                image_exist=$(docker image ls |grep $img)
                if [ "$image_exist" ]
                then
                    docker image ls -q $img | xargs docker image rm -f
                fi
            done
        done

}

function Remove_faas_images(){
    file_list=$(grep -r 'image:' $basepath/install/kubernetes/kube_openfaas_yaml|awk {'print $1'}|cut -d ":" -f 1)
    for f in $file_list
        do
            image_list=$(grep 'image:' $f|awk {'print $2'}|cut -d ":" -f 1)
            for img in $image_list
            do
                image_exist=$(docker image ls |grep $img)
                if [ "$image_exist" ]
                then
                    docker image ls -q $img | xargs docker image rm -f
                fi
            done
        done

}


function Remove_k8s_images(){
    image_list=$(docker image ls |grep k8s|awk {'print $1'})
    for img in $image_list
        do
            docker image ls -q $img | xargs docker image rm -f
        done
    image_list=$(docker image ls |grep flannel|awk {'print $1'})
    for img in $image_list
        do
            docker image ls -q $img | xargs docker image rm -f
        done

}

Reset_k8s_system
Remove_dir
Remove_function_images
Remove_edgescale_images
Remove_faas_images
Remove_k8s_images
