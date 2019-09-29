# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import re
import shutil
import sys
import json


def build_function(rootPath, function_name, docker_repo, docker_sub_dir):
  template_path = os.path.join(rootPath, "build/openfaas_template")
  os.chdir(template_path)
  try:
    if os.system("which faas") != 0:  # check that the faas-cli is installed
      install_code = os.system("curl -sSL https://cli.openfaas.com | sudo sh")
      if install_code != 0:
        raise Exception("failed to intall openfaas cli, please check your network.")
    os.system("faas new --lang=python3-es {}".format(function_name))
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
      os.system("faas build -f {}.yml".format(function_name))
      print("-------build service {} complete-------".format(function_name))
      shutil.rmtree(path)
      shutil.rmtree(os.path.join(template_path, "build"))
      os.remove("{}.yml".format(function_name))
      os.system("docker tag {0}:latest {1}/{2}/{0} ".format(function_name, docker_repo, docker_sub_dir))
      os.system("docker push {0}/{1}/{2} ".format(docker_repo, docker_sub_dir, function_name))
    else:
      raise Exception("Failed to build function")
  except Exception as e:
    print(e)
    sys.exit()


def build_service(service_path, service_name, docker_repo, docker_sub_dir, tag="latest"):
  if service_name == "kong":
    os.chdir(os.path.split(os.path.split(service_path)[0])[0])
    os.system("docker build -t %s:%s -f %s ." % (service_name, tag,
                                                 os.path.join(service_path, "Dockerfile")))
  else:
    os.chdir(service_path)
    if os.path.exists(os.path.join(service_path, "Makefile")):
      os.system("make")
      os.chdir(os.path.join(service_path, "build"))
      os.system("docker build -t %s:%s ." % (service_name, tag))
      os.chdir(service_path)
      os.system("make clean")
    else:
      os.system("docker build -t %s:%s ." % (service_name, tag))
  os.system("docker tag {0}:{1} {2}/{3}/{0}:{1} ".format(service_name, tag, docker_repo, docker_sub_dir))
  os.system("docker push {0}/{1}/{2}:{3} ".format(docker_repo, docker_sub_dir, service_name, tag))
  print("-------build service {} complete-------".format(service_name))


def main(tag="latest"):
  rootPath = os.path.split(sys.path[0])[0]
  config_path = os.path.join(rootPath, "install/kubernetes/config/vars.json")
  with open(config_path,"r") as f:
      config_data = json.load(f)
  docker_repo = config_data.get("env").get("harbor_domain")
  docker_sub_dir = config_data.get("env").get("harbor_respo_subdir")
  docker_user = config_data.get("env").get("harbor_user")
  docker_userpasswd = config_data.get("env").get("harbor_pass")
  docker_remot_ip = config_data.get("env").get("harbor_ip_address")
  if os.popen("grep -rn '{0}' /etc/hosts|wc -l".format(docker_repo)).read()[0] == '0':
    os.system("sudo sed -i '$a {0} {1}' /etc/hosts".format(docker_remot_ip, docker_repo))
  os.system("docker login -p {0} -u {1} {2}".format(docker_userpasswd, docker_user, docker_repo))
  function_path = os.path.join(rootPath, "services/functions")
  allFunction_dirs = [f for f in os.listdir(function_path) if re.match("scale_*", f)]
  for function_dir in allFunction_dirs:
    function_name = os.path.split(function_dir)[-1].replace('_', '-')
    # build function docker images
    build_function(rootPath, function_name, docker_repo, docker_sub_dir)

  # find all the paths need to build based on dockerfile
  serviceBase_path = os.path.join(rootPath, "services")
  service_names = [f for f in os.listdir(serviceBase_path) if not re.match("functions", f)]
  for name in service_names:
    service_path = os.path.join(serviceBase_path, name)
    build_service(service_path, name, docker_repo, docker_sub_dir, tag)


if __name__ == '__main__':
  docker_tag = "latest"
  main(docker_tag)
