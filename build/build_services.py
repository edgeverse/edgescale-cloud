# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import re
import shutil
import sys
import json


def command(cmd):
    if os.system(cmd) != 0:
        return "error"


def build_function(rootPath, function_name, docker_repo, docker_sub_dir):
    template_path = os.path.join(rootPath, "build/openfaas_template")
    os.chdir(template_path)
    try:
        if os.system("which faas") != 0:  # check that the faas-cli is installed
            install_code = os.system("curl -sSL https://cli.openfaas.com | sudo sh")
            if install_code != 0:
                raise Exception("failed to intall openfaas cli, please check your network.")
        command("faas new --lang=python3-es {}".format(function_name))
        path = os.path.join(template_path, function_name)
        if os.path.exists(path):
            shutil.rmtree(path)
            function_path = os.path.join(rootPath, "services/functions")
            shutil.copytree(os.path.join(function_path, function_name.replace("-", "_")),
                            path)
            shutil.copytree(os.path.join(function_path, "edgescale_pymodels"),
                            os.path.join(path, "edgescale_pymodels"))
            shutil.copytree(os.path.join(function_path, "edgescale_pyutils"),
                            os.path.join(path, "edgescale_pyutils"))
            if command("faas build {} -f {}.yml".format(generate_build_args(), function_name)) == "error":
                shutil.rmtree(path)
                shutil.rmtree(os.path.join(template_path, "build"))
                os.remove("{}.yml".format(function_name))
                raise Exception("failed to deploy function, please retry again!")
            shutil.rmtree(path)
            shutil.rmtree(os.path.join(template_path, "build"))
            os.remove("{}.yml".format(function_name))
            command("docker tag {0}:latest {1}/{2}/{0} ".format(function_name, docker_repo, docker_sub_dir))
            command("docker push {0}/{1}/{2} ".format(docker_repo, docker_sub_dir, function_name))
        else:
            raise Exception("Failed to build function")
    except Exception as e:
        print(e)
        sys.exit()


def generate_build_args():
    build_args = ""
    if os.environ.get("http_proxy"):
        build_args += " --build-arg http_proxy='%s'" % os.environ.get("http_proxy")
    if os.environ.get("https_proxy"):
        build_args += " --build-arg https_proxy='%s'" % os.environ.get("https_proxy")
    if os.environ.get("all_proxy"):
        build_args += " --build-arg all_proxy='%s'" % os.environ.get("all_proxy")
    return build_args


def build_service(service_path, service_name, docker_repo, docker_sub_dir, tag="latest"):
    build_args = generate_build_args()
    if service_name == "kong":
        os.chdir(os.path.split(os.path.split(service_path)[0])[0])
        if command("docker build %s -t %s:%s -f %s ." % (build_args, service_name, tag,
                                                         os.path.join(service_path, "Dockerfile"))) == "error":
            return "error"
    else:
        os.chdir(service_path)
        if os.path.exists(os.path.join(service_path, "Makefile")):
            command("make")
            os.chdir(os.path.join(service_path, "build"))
            if command("docker build %s -t %s:%s ." % (build_args, service_name, tag)) == "error":
                return "error"
            os.chdir(service_path)
            command("make clean")
        else:
            if command("docker build %s -t %s:%s ." % (build_args, service_name, tag)) == "error":
                return "error"
    command("docker tag {0}:{1} {2}/{3}/{0}:{1} ".format(service_name, tag, docker_repo, docker_sub_dir))
    command("docker push {0}/{1}/{2}:{3} ".format(docker_repo, docker_sub_dir, service_name, tag))


def main(tag="latest"):
    rootPath = os.path.split(sys.path[0])[0]
    config_path = os.path.join(rootPath, "install/kubernetes/config/vars.json")
    with open(config_path, "r") as f:
        config_data = json.load(f)
    docker_repo = config_data.get("env").get("harbor_domain")
    docker_sub_dir = config_data.get("env").get("harbor_project_name")
    docker_user = config_data.get("env").get("harbor_user")
    docker_userpasswd = config_data.get("env").get("harbor_passwd")
    docker_remot_ip = config_data.get("env").get("harbor_host_ip")
    if os.popen("grep -rn '{0}' /etc/hosts|wc -l".format(docker_repo)).read()[0] == '0':
        command("sudo sed -i '$a {0} {1}' /etc/hosts".format(docker_remot_ip, docker_repo))
    command("docker login -p {0} -u {1} {2}".format(docker_userpasswd, docker_user, docker_repo))
    function_path = os.path.join(rootPath, "services/functions")
    allFunction_dirs = [f for f in os.listdir(function_path) if re.match("scale_*", f)]
    success_number = 0
    failed_list = []
    for function_dir in allFunction_dirs:
        function_name = os.path.split(function_dir)[-1].replace('_', '-')
        # build function docker images
        if build_function(rootPath, function_name, docker_repo, docker_sub_dir) == "error":
            failed_list.append(function_name)
            continue
        success_number += 1
    # find all the paths need to build based on dockerfile
    serviceBase_path = os.path.join(rootPath, "services")
    service_names = [f for f in os.listdir(serviceBase_path) if not re.match("functions", f)]
    for name in service_names:
        service_path = os.path.join(serviceBase_path, name)
        if build_service(service_path, name, docker_repo, docker_sub_dir, tag) == "error":
            failed_list.append(name)
            continue
        success_number += 1
    print(
        "Build summary: success : {0}, failed_number : {1}, failed_name : {2}.".format(success_number, len(failed_list),
                                                                                       failed_list))

if __name__ == '__main__':
    docker_tag = "latest"
    main(docker_tag)
