# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

import os 
import json
import psycopg2


def connect_sql(config_data,sql,db_tag=""):
    try:
        db_info = config_data.get("db")
        if db_tag != "kong":
            User = db_info.get("pg_user")
            Database = db_info.get("pg_database")
            Password = db_info.get("pg_pass")
        else:
            User = db_info.get("kong_user")
            Database = db_info.get("kong_database")
            Password = db_info.get("kong_pass")
        connection = psycopg2.connect(
                    user = User,
                    password = Password,
                    host = db_info.get("pg_host"),
                    database = Database,
                    port = "5432"
                )
        cursor = connection.cursor() 
        a = cursor.execute(sql)
        print("Update success")
        connection.commit() 
    except(Exception, psycopg2.Error) as error:
        raise("connecting to postgres Error:", error)
    finally:
        cursor.close()
        connection.close()


def read_config(path):
    with open(path,"r") as f:
        config_data = json.load(f)
        return config_data 


#change the config database table
def updater(config_data):
    # Parse database parameters for edgescale service
    config_template = read_config(path="./database_config.json").get("settings")
    config_keys = list(config_template.keys())
    for i in config_keys:
        if not config_template[i]:
            config_template[i] = config_data.get("service").get(i)
    data = {}
    data["settings"] = config_template
    config_sql = "UPDATE config SET text = '{0}' WHERE cast(text->'settings'->>'DEBUG' as bool) = true;".format(json.dumps(data))
    connect_sql(config_data,config_sql)
    # Parse databse parameters for kong service
    api_name = "api." + config_data.get("env").get("domain_name")
    api_sql = "UPDATE snis SET name= '{0}' WHERE certificate_id='21b69eab-09d9-40f9-a55e-c4ee47fada68';".format(api_name)
    connect_sql(config_data,api_sql,db_tag="kong")
    root_path = os.path.abspath(os.path.join(os.getcwd(), "../../.."))
    ssl_cert_path = root_path + config_data.get("ssl").get("cert_path")
    ssl_key_path = root_path + config_data.get("ssl").get("key_path")
    ssl_cert = open(ssl_cert_path,"r").read()
    ssl_key = open(ssl_key_path,"r").read() 
    cert_sql = "UPDATE certificates SET cert='{0}', key='{1}' WHERE id='21b69eab-09d9-40f9-a55e-c4ee47fada68';".format(ssl_cert,ssl_key)
    connect_sql(config_data,cert_sql,db_tag="kong")


if __name__ == "__main__":
    path = r"./vars.json"
    config_data = read_config(path)
    updater(config_data)
