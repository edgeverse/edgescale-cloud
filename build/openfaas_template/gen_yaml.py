# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os
import sys
import json

template_yaml = """
provider:
  name: faas
  gateway: http://127.0.0.1:31112

functions:
  {0}:
    lang: python3-es
    handler: ./{0}
    image: {1}/{2}/{0}
    secrets:
      - faas-repos
    environment: 
      imagePullPolicy: IfNotPresent
      mqtopic: v1
"""


def handler(scale_list):
    rootPath = os.path.split(os.path.split(sys.path[0])[0])[0]
    config_path = os.path.join(rootPath, "install/kubernetes/config/vars.json")
    with open(config_path, "r") as f:
        config_data = json.load(f)
    docker_repo = config_data.get("env").get("harbor_domain")
    docker_sub_dir = config_data.get("env").get("harbor_project_name")
    for fi in scale_list:
        with open("{}.yml".format(fi), 'w') as f:
            f.write(template_yaml.format(fi, docker_repo, docker_sub_dir))


if __name__ == "__main__":
    scale_list = ["scale-app", "scale-device", "scale-other", "scale-role", "scale-solution", "scale-task",
                  "scale-user"]
    handler(scale_list)
