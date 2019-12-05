# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP


query_user_models_sql = '''
SELECT M.id, M.model, M.type, M.platform, M.vendor, M.is_public
FROM dcca_models AS M
WHERE M.owner_id = {user_id} 
'''

query_user_solutions_sql = '''
SELECT 
  S.id, solution,
  M.model, M.type, M.platform, M.vendor, 
  S.image, S.version, S.link, S.is_public
FROM 
  dcca_ass_solution_images AS S 
LEFT JOIN dcca_models AS M 
  ON S.model_id = M.id 
WHERE 
  S.owner_id = {uid} 
  AND S.logical_delete_flag IS FALSE 
'''

query_user_applications_sql = '''
SELECT A.id, A.name, A.display_name, A.description, A.likes, A.stars, A.created_at, A.is_public, A.in_store
FROM dcca_applications AS A 
WHERE A.owner_id = {uid} 
'''

count_solutions_sql = '''
SELECT count(id) 
FROM 
  dcca_ass_solution_images AS S 
WHERE 
  S.owner_id = {uid} 
  AND S.logical_delete_flag IS FALSE 
'''

count_models_sql = '''
SELECT count(id) 
FROM dcca_models AS M 
WHERE M.owner_id = {uid}
'''

count_applications_sql = '''
SELECT count(id) 
FROM dcca_applications AS A 
WHERE A.owner_id = {uid}
'''


query_user_device_pos_sql = '''
SELECT DP.id, DP.latitude, DP.longitude, DP.ip_address, LOC.name  
FROM dcca_device_position AS DP 
LEFT JOIN dcca_locations AS LOC 
ON LOC.id = DP.location_id
LEFT JOIN dcca_ass_user_device AS AUD 
ON AUD.device_id = DP.id
WHERE AUD.user_id = {uid}
'''

query_device_pos_count_sql = '''
SELECT LOC.name, count(*) AS counts 
FROM dcca_device_position AS DP 
LEFT JOIN dcca_locations AS LOC 
ON LOC.id = DP.location_id 
LEFT JOIN dcca_ass_user_device AS AUD 
ON AUD.device_id = DP.id 
WHERE AUD.user_id = {uid}
GROUP BY LOC.name 
'''

query_models_sql = '''
SELECT 
  id, 
  model,
  type,
  platform, 
  vendor,
  is_public,
  owner_id
FROM
  dcca_models
WHERE
'''

query_total_models_sql = '''
SELECT
  count(id)
FROM
  dcca_models
WHERE
'''

query_my_model_sql = '''
SELECT 
  id, 
  model,
  type,
  platform, 
  vendor,
  is_public,
  owner_id
FROM
  dcca_models
WHERE
  owner_id={uid}
'''

query_total_my_models_sql = '''
SELECT
  count(id)
FROM
  dcca_models
WHERE
  owner_id={uid}
'''

ACCOUNT_TYPE_ID_OEM = 2
ACCOUNT_TYPE_ID_ODM = 3
query_user_account_type_sql = '''
SELECT 
  count(id) 
FROM 
  dcca_users AS U 
WHERE 
  (account_type_id={} OR account_type_id={}) 
  AND id=%s ;
'''.format(ACCOUNT_TYPE_ID_OEM, ACCOUNT_TYPE_ID_ODM)

# Query if model exist
query_model_sql = '''
SELECT count(id)
FROM
  dcca_models AS M
WHERE 
  M.model=%s
  AND M.type=%s
  AND M.platform=%s
  AND M.vendor=%s ;
'''

query_max_limit_sql = '''
SELECT
  max_limit
FROM
  dcca_user_limits
WHERE 
  user_id=%s
  AND limit_type_id=%s ;
'''

query_model_by_id_sql = '''
SELECT
  M.id, 
  M.model, 
  M.type, 
  M.platform, 
  M.vendor,
  M.is_public,
  M.owner_id
FROM
  dcca_models AS M
WHERE 
  M.id=%s;
'''

update_model_by_id_sql = "UPDATE dcca_models SET model=%s, type=%s, platform=%s, vendor=%s WHERE id=%s ;"


count_all_models_sql = 'SELECT count(id) FROM dcca_models WHERE owner_id=%s ;'
count_model_owner_sql = 'SELECT count(id) FROM dcca_models WHERE id=%s AND owner_id=%s ;'
delete_model_by_id_sql = 'DELETE FROM dcca_models WHERE id=%s ;'

binding_to_devices_sql = "SELECT count(id) FROM hosts WHERE dcca_model_id=%s;"
binding_to_solutions_sql = "SELECT count(id) FROM dcca_ass_solution_images WHERE model_id=%s ;"
binding_to_ass_host_model_sql = "SELECT count(*) FROM dcca_ass_host_model WHERE model_id=%s ;"

bind_model_owner_sql = 'SELECT name FROM hosts WHERE dcca_model_id=%s;'

query_devive_name_sql = 'SELECT name FROM hosts WHERE id=%s AND owner_id=%s;'

query_solution_name_sql = 'SELECT solution FROM dcca_ass_solution_images WHERE model_id=%s AND owner_id=%s;'

count_model_exist_sql = 'SELECT count(*) FROM dcca_models WHERE id=%s AND (owner_id=%s OR is_public=TRUE) ;'

query_service_by_model_sql = '''
SELECT 
  S.id AS service_id, 
  S.uid
FROM
  dcca_ass_model_service AS MS
LEFT JOIN dcca_services AS S
  ON MS.service_id = S.id 
WHERE 
  MS.model_id=%s ;
'''

query_service_by_id_sql = '''
SELECT 
  uid, name, protocal, cipher_suite,
  server_certificate_format, server_certificate_key, 
  connection_url, config,
  signing_certificate_format, signing_certificate_key
FROM
  dcca_services AS S
WHERE 
  S.user_id=%s
  AND S.uid=%s ;
'''

query_all_registries_sql = '''
SELECT 
  id, name, is_public, description, created_at
FROM 
  dcca_app_mirror 
WHERE 
'''

query_total_registries_sql = '''
SELECT 
  count(id)
FROM 
  dcca_app_mirror 
WHERE
'''

# Create a docker registry
create_registry_sql = '''
INSERT INTO dcca_app_mirror (name, is_public, user_id) VALUES ('{name}', {is_public}, {user_id});
'''

# Query user name
query_name_sql = '''
SELECT username,email FROM dcca_users WHERE id=%s;
'''

# Query one registry by id
query_registry_sql = '''
SELECT
  id, name, is_public, description, user_id
FROM
  dcca_app_mirror
WHERE 
  id in ({registry_ids});
'''

# Delete docker registry
remove_registry_sql = '''
DELETE FROM dcca_app_mirror WHERE id in ({registry_ids});
'''

# Delete softapp
remove_softapp_sql = '''
DELETE FROM dcca_softapps WHERE mirror_id in ({mirror_ids});
'''

# Query softapp
query_softapps_sql = '''
SELECT id FROM dcca_softapps WHERE mirror_id in ({mirror_ids});
'''

# Delete es_task_da_inst
remove_da_inst_sql = '''
DELETE FROM es_task_da_inst WHERE softapp_id={softapp_id};
'''

count_all_services_sql = '''
SELECT count(S.id) 
FROM 
  dcca_services AS S
WHERE 
  S.user_id=%s ;
'''

query_all_services_sql = '''
SELECT 
  uid, name, protocal, cipher_suite,
  server_certificate_format, server_certificate_key, 
  connection_url, config,
  signing_certificate_format, signing_certificate_key
FROM
  dcca_services AS S
WHERE 
  S.user_id=%s 
LIMIT %s
OFFSET %s ;
'''

create_service_sql = '''
INSERT INTO dcca_services 
  (name, protocal, cipher_suite, server_certificate_format, server_certificate_key,
  connection_url, config, signing_certificate_format, signing_certificate_key, user_id)
VALUES 
  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;
'''

update_service_uid_sql = 'UPDATE dcca_services SET uid=%s WHERE id=%s;'

create_service_model_map_sql = 'INSERT INTO dcca_ass_model_service (model_id, service_id) VALUES (%s, %s)'

query_all_common_service_sql = '''
SELECT
  S.id, name, url, port, access_token
FROM
  dcca_common_services AS S
WHERE 
  S.user_id=%s ;
'''

query_server_cert_format_sql = 'SELECT enum_range(NULL::server_certificate_format) ;'

query_signing_cert_format_sql = 'SELECT enum_range(NULL::signing_certificate_format) ;'

delete_service_by_id_sql = '''
DELETE FROM dcca_services WHERE uid=%s ;
'''

count_user_service_sql = '''
SELECT
  count(S.id)
FROM
  dcca_common_services AS S
WHERE 
  user_id=%s
  AND S.id=%s ;
'''

update_service_sql = '''
UPDATE 
  dcca_common_services
SET 
  name=%s, url=%s, port=%s, access_token=%s
WHERE 
  id=%s ;
'''

remove_one_service_sql = 'DELETE FROM dcca_common_services WHERE id=%s ;'

query_owner_devices_sql = '''
SELECT
  D.id, D.name, D.display_name
FROM
  hosts AS D
LEFT JOIN dcca_ass_user_device AS UD
  ON D.id=UD.device_id
WHERE
  UD.user_id=%s
  AND ({_sql_str})
ORDER BY D.id DESC ;
'''

# Check if is device owner
check_device_owner_sql = '''
SELECT count(1) 
FROM 
  dcca_ass_user_device AS UD
WHERE 
  UD.user_id=%s
  AND UD.device_id=%s;
'''

query_deploy_limits_sql = '''
SELECT
  max_limit
FROM
  dcca_user_limits AS UL
WHERE 
  user_id=%s
  AND limit_type_id=%s;
'''

query_per_time_limit_sql = 'SELECT max_limit, max_sec' \
                           ' FROM dcca_user_limits' \
                           ' WHERE' \
                           '  user_id=%s' \
                           '  AND limit_type_id=%s ;'

# Query device by id
query_device_by_id_sql = '''
SELECT 
  D.name
FROM
  hosts AS D
WHERE 
  D.id=%s;
'''

select_softapps_sql = '''
SELECT
  SA.id, 
  SA.name AS docker_image_name,
  AM.name AS registry_name,
  SA.image_name,
  SA.commands, 
  SA.args,
  SA.hostnetwork,
  SA.ports,
  SA.volumes,
  SA.volume_mounts,
  SA.cap_add,
  SA.morepara,
  A.name AS app_name
FROM
  dcca_softapps AS SA
LEFT JOIN dcca_app_mirror AS AM
  ON SA.mirror_id = AM.id
LEFT JOIN dcca_applications AS A
  ON SA.application_id = A.id
WHERE
  SA.application_id=%s
  AND SA.version=%s;
'''

create_deploy_record_sql = '''
INSERT INTO dcca_deploy_recoreds 
  (event, template, raw_k8s_result, parsed_k8s_result, resource, task_id, device_id) 
VALUES (%s, %s, %s, %s, %s, %s, %s);
'''

create_model_sql = 'INSERT INTO dcca_models (model, type, platform, vendor, owner_id) ' \
                   'VALUES (%s, %s, %s, %s, %s) RETURNING id;'
create_common_service_sql = '''
INSERT INTO dcca_common_services
  (name, url, port, access_token, user_id)
VALUES 
  (%s, %s, %s, %s, %s) 
RETURNING id;
'''

query_my_model_sql = '''
SELECT 
  id, 
  model,
  type,
  platform, 
  vendor,
  is_public,
  owner_id
FROM
  dcca_models
WHERE
  owner_id={uid}
'''

query_total_my_models_sql = '''
SELECT
  count(id)
FROM
  dcca_models
WHERE
  owner_id={uid}
'''

query_one_model_sql = 'SELECT count(id) FROM dcca_models WHERE id=%s AND owner_id=%s;'

create_audit_sql = 'INSERT INTO dcca_audit (user_id, comments, approve_type, approve_item, to_public) VALUES (%s, %s, %s, %s, %s) RETURNING id;'

query_audit = '''
SELECT
  A.id, A.approved, A.comments, U.username, A.created_at, A.status, A.approve_type
From
  dcca_audit as A
LEFT JOIN dcca_users AS U ON A.user_id = U.id
'''

query_total_audit = '''
SELECT
 count(A.id)
From
  dcca_audit as A
LEFT JOIN dcca_users AS U ON A.user_id = U.id
'''

query_one_audit = 'SELECT id, approved, approve_item, to_public, status FROM dcca_audit WHERE id=%s;'

update_model_sql = 'UPDATE dcca_models SET is_public=%s WHERE id=%s;'

update_audit_sql = 'UPDATE dcca_audit SET approved=%s, status=%s WHERE id=%s;'

query_device_owner_by_mid_sql = 'SELECT owner_id from hosts WHERE dcca_model_id=%s'
