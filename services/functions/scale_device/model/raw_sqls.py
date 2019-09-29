# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

query_device_limit_sql = 'SELECT max_limit FROM dcca_user_limits WHERE user_id=%s AND limit_type_id=%s;'

count_current_devices_sql = 'SELECT count(*) FROM hosts WHERE owner_id=%s OR oem_uid=%s;'
query_all_device_by_uid = 'SELECT name, online FROM hosts WHERE owner_id=%s LIMIT %s OFFSET %s;'

# TODO
insert_ass_device_model_sql = '''INSERT INTO dcca_ass_host_model
  (host_id, model_id)
VALUES
  (%s, %s);
'''

# Query one user's device 20170311 Jiapeng-b52813
query_one_device_sql = 'SELECT count(*) FROM hosts WHERE id=%s AND owner_id=%s OR oem_uid=%s;'

delete_ass_host_model_sql = "DELETE FROM dcca_ass_host_model WHERE host_id=%s ;"
delete_ass_user_host_sql = 'DELETE FROM dcca_ass_user_device WHERE device_id=%s;'
delete_ass_device_tag_sql = 'DELETE FROM dcca_ass_device_tag WHERE device_id=%s;'
delete_progress_sql = 'DELETE FROM dcca_progress WHERE device_id=%s;'
delete_ass_device_task_sql = 'DELETE FROM dcca_ass_device_task WHERE device_id=%s;'
delete_solution_task_sql = 'DELETE FROM dcca_tasks WHERE device_id=%s ;'
delete_device_sql = 'DELETE FROM hosts WHERE id=%s ;'
delete_deploy_record_sql = 'DELETE FROM dcca_deploy_recoreds WHERE device_id=%s;'
query_task_by_inst_sql = 'SELECT DISTINCT task_id FROM es_task_da_inst WHERE device_id=%s ;'
delete_task_inst_sql = 'DELETE FROM es_task_da_inst WHERE device_id=%s ;'
count_task_inst_sql = 'SELECT count(*) FROM es_task_da_inst WHERE task_id=%s ;'
delete_task_by_id_sql = 'DELETE FROM es_tasks WHERE id=%s ;'
delete_ota_task_inst_sql = 'DELETE FROM es_task_ota_inst WHERE device_id=%s ;'
delete_group_device_id_sql = 'DELETE FROM dcca_ass_device_group WHERE device_id=%s ;'

# Make the user the owner of device
create_device_owner_sql = '''
INSERT INTO dcca_ass_user_device (user_id, device_id) VALUES (%s, %s);
'''

query_device_tags_sql_v2 = '''
SELECT 
  ADT.device_id,
  T.id AS tag_id, 
  T.name AS tag_name
FROM dcca_ass_device_tag AS ADT
LEFT JOIN dcca_tags AS T
  ON ADT.tag_id=T.id
WHERE
  ADT.device_id IN %s;
'''

check_device_owner_v2_sql = 'SELECT count(1) FROM dcca_ass_user_device WHERE user_id=%s AND device_id IN %s ;'


# Query device location information
query_device_location_info_v2_sql = '''
SELECT
  D.id,
  D.name,
  L.name AS location,
  D.display_name
FROM
  hosts AS D
LEFT JOIN dcca_ass_user_device AS AUD
  ON D.id=AUD.device_id
LEFT JOIN dcca_device_position AS DP
  ON D.id=DP.id
LEFT JOIN dcca_locations AS L
  ON DP.location_id=L.id
WHERE
  AUD.user_id=%s
  AND AUD.device_id IN %s
LIMIT %s
OFFSET %s ;
'''

# Query user device positions
query_device_positions_sql = '''
SELECT
  P.id AS device_id,
  P.latitude AS lat,
  P.longitude AS lng
FROM
  dcca_device_position AS P
LEFT JOIN dcca_ass_user_device AS AUD
  ON P.id = AUD.device_id
WHERE
  AUD.user_id=%s
LIMIT %s
OFFSET %s;
'''


# Query all user device positions
query_all_positions_sql = '''
SELECT
  P.id AS device_id,
  P.latitude AS lat,
  P.longitude AS lng
FROM
  dcca_device_position AS P
LEFT JOIN dcca_ass_user_device AS AUD
  ON P.id = AUD.device_id
LIMIT %s
OFFSET %s;
'''

create_device_sql = 'INSERT INTO hosts (name, certname, owner_id, dcca_model_id, display_name, lifecycle, oem_uid) ' \
                    ' VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;'

query_device_v2_sql = '''
SELECT 
  D.id,
  D.name,
  D.certname,
  D.created_at,
  D.updated_at,
  D.last_report,
  D.display_name,
  S.solution,
  S.version
FROM
  hosts AS D
LEFT JOIN dcca_ass_solution_images AS S
  ON D.solution_id = S.id
WHERE D.id=%s ;
'''

query_user_bind_model_sql = 'SELECT count(*) FROM hosts WHERE dcca_model_id=%s AND owner_id=%s;'

update_device_sql = 'UPDATE hosts SET display_name=%s WHERE id=%s ;'

count_lifecycle_status_sql = 'SELECT count(id) FROM hosts WHERE owner_id=%s AND lifecycle=%s;'

query_oem_users_by_device_name_sql = 'SELECT oem_uid,name FROM hosts where name=%s;'

bind_device_owner_sql = 'UPDATE hosts SET owner_id=%s WHERE name=%s and owner_id=%s RETURNING id;'

change_device_status_sql = 'UPDATE hosts SET lifecycle=%s WHERE id=%s;'

query_location_sql_v2 = '''

SELECT DISTINCT L.name AS country
FROM
  dcca_locations AS L
RIGHT JOIN dcca_device_position AS P
  ON P.location_id=L.id
WHERE
  P.id IN (SELECT D.id FROM hosts AS D WHERE D.owner_id=%s);
'''

# Query all the available platforms
query_platform_command = '''
SELECT DISTINCT platform
FROM
  dcca_models
ORDER BY platform;
'''

query_by_country_sql = '''
SELECT
  D.id, D.name
FROM
  hosts AS D
INNER JOIN dcca_device_position AS DP
  ON D.id=DP.id
LEFT JOIN dcca_locations AS L
  ON DP.location_id=L.id
LEFT JOIN dcca_ass_user_device AS AUD
  ON D.id=AUD.device_id
WHERE
  AUD.user_id={user_id}
  AND L.name='{country}'
ORDER BY D.id
LIMIT {limit} OFFSET {offset};
'''

query_by_country_sql_v2 = '''
SELECT
  D.id, D.name
FROM
  hosts AS D
INNER JOIN dcca_device_position AS P
  ON D.id=P.id
WHERE
  D.owner_id=%s
  AND P.location_id=(SELECT id FROM dcca_locations AS L WHERE L.name=%s)

ORDER BY D.id
LIMIT %s
OFFSET %s;
'''

query_by_platform_sql = '''
SELECT
  D.id, D.name
FROM
  hosts AS D
LEFT JOIN dcca_ass_user_device AS AUD
  ON D.id=AUD.device_id
LEFT JOIN dcca_ass_host_model AS ADM
  ON D.id=ADM.host_id
LEFT JOIN dcca_models AS M
  ON ADM.model_id=M.id
WHERE
  AUD.user_id={user_id}
  AND M.platform='{platform}'
ORDER BY D.id
LIMIT {limit} OFFSET {offset};
'''

query_by_platform_sql_v2 = '''
SELECT
  D.id, D.name
FROM
  hosts AS D
LEFT JOIN dcca_models AS M
  ON D.dcca_model_id=M.id
WHERE
  D.owner_id=%s
  AND M.platform=%s
ORDER BY D.id
LIMIT %s OFFSET %s;
'''

query_device_by_solution_sql = '''
SELECT 
  D.id, D.name
FROM 
  hosts AS D
LEFT JOIN dcca_ass_solution_images AS ASI
  ON D.dcca_model_id=ASI.model_id
WHERE
  D.owner_id={uid}
  AND ASI.id={solution_id}
LIMIT {limit}
OFFSET {offset};
'''

query_all_location_info_sql = '''
SELECT
  D.id,
  D.name,
  C.name AS continent,
  C.short_name AS short
FROM
  hosts AS D
LEFT JOIN dcca_ass_user_device AS AUD
  ON D.id = AUD.device_id
LEFT JOIN dcca_device_position AS P
  ON AUD.device_id=P.id
LEFT JOIN dcca_continents AS C
  ON P.continent_id=C.id
WHERE
  AUD.user_id={user_id}
LIMIT {limit}
OFFSET {offset};
'''

query_all_location_info_sql_v2 = '''
SELECT
  D.id,
  D.name,
  D.online,
  P.continent_id
FROM
  hosts AS D,
  dcca_device_position AS P
WHERE 
  D.owner_id=%s
  AND D.id=P.id
LIMIT %s
OFFSET %s ;
'''


query_device_by_name_sql = '''
SELECT 
  D.id,
  DP.id AS position_id
FROM 
  hosts AS D
LEFT JOIN dcca_device_position AS DP
  ON D.id=DP.id
WHERE 
  D.name='{device_name}';
'''

create_device_position_sql = '''
INSERT INTO dcca_device_position
  (id, ip_address, location_id, continent_id, latitude, longitude)
VALUES (%s, %s, %s, %s, %s, %s);
'''

update_device_position_sql = '''
UPDATE dcca_device_position 
SET 
  ip_address=%s,
  location_id=%s,
  continent_id=%s,
  latitude=%s,
  longitude=%s
WHERE id=%s;
'''

query_location_sql = '''
SELECT id FROM dcca_locations WHERE name='{name}';
'''

create_location_sql = '''
INSERT INTO dcca_locations (name) VALUES ('{name}') RETURNING ID;
'''

query_continent_sql = '''
SELECT id FROM dcca_continents WHERE short_name='{continent}';
'''

query_device_message = '''
SELECT
  D.owner_id AS device_owner_id,
  M.id AS model_id,
  M.is_public AS model_permission,
  M.owner_id AS model_owner_id,
  M.default_solution_id AS model_default_solution_id
FROM
  hosts AS D
LEFT JOIN dcca_models AS M
  ON D.dcca_model_id=M.id
WHERE
  D.name=%s
'''

count_solutions = '''
SELECT
  count(*)
FROM
  dcca_ass_solution_images
WHERE
  model_id=%s
  AND owner_id=%s
  AND logical_delete_flag IS FALSE
'''

query_solutions_by_device_sql = '''
SELECT
  S.id AS sol_id,
  D.id AS device_id,
  M.id AS model_id,
  M.model AS model,
  M.type AS type,
  M.platform AS platform,
  M.vendor AS vendor,
  S.solution AS solution,
  S.version AS version,
  S.link AS url,
  S.public_key AS public_key,
  S.is_signed AS is_signed,
  S.have_installer AS have_installer
FROM
  hosts AS D
LEFT JOIN dcca_ass_host_model AS AHM
  ON D.id=AHM.host_id
LEFT JOIN dcca_models AS M
  ON D.dcca_model_id=M.id
LEFT JOIN dcca_ass_solution_images AS S
  ON M.id=S.model_id
WHERE 
  D.name='{device_name}'
  AND S.logical_delete_flag IS FALSE
'''

remove_tag_from_device_sql = '''
DELETE FROM dcca_ass_device_tag
WHERE
  device_id=%s
  AND tag_id=%s;
'''

query_tag_sql = '''
SELECT id FROM dcca_tags WHERE name=%s;
'''

create_tag_sql = '''
INSERT INTO dcca_tags (name) VALUES ('{name}') RETURNING id;
'''

count_not_owned_devices_sql = '''
SELECT
  count(UD.user_id)
FROM
  dcca_ass_user_device AS UD
WHERE
  UD.user_id={user_id} AND UD.device_id IN ({device_ids});
'''

attach_tag_to_devices_sql = '''
INSERT INTO
  dcca_ass_device_tag
VALUES {device_tag_ids_str}
ON CONFLICT
ON CONSTRAINT
  dcca_ass_device_tag_device_id_tag_id_pk
DO NOTHING;
'''

query_all_tags_sql = '''
SELECT
  T.id, 
  T.name AS tag_name
FROM dcca_tags AS T;
'''

check_device_owner_sql = '''
SELECT 
  count(*)
FROM
  hosts AS D
LEFT JOIN dcca_ass_user_device AS UD
  ON D.id=UD.device_id
WHERE 
  UD.device_id=%s
  AND UD.user_id=%s
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

query_device_model_by_uid_sql = '''
SELECT
  certname,
  M.model,
  M.type,
  M.platform,
  M.vendor
FROM
  hosts AS H
LEFT JOIN dcca_models AS M ON H.dcca_model_id=M.id
WHERE
  left(H.certname,32)='{uid}';'''


query_model_by_did = '''
SELECT
  name
FROM
  hosts 
WHERE name LIKE %(like)s;
'''

query_oem_by_model = '''
SELECT
  owner_id, chain
FROM
  dcca_models AS M
LEFT JOIN
  dcca_certificates
ON
  user_id = owner_id
WHERE
  (M.model, M.type, M.platform, M.vendor) = (%s, %s, %s, %s)
'''

query_services_by_uid = '''
SELECT
  name, url, port, access_token
FROM
  dcca_common_services
WHERE
  user_id=%s ;
'''

update_device_lifecycle_by_device_name = '''UPDATE hosts SET lifecycle=%s WHERE name=%s;'''

query_device_current_status = '''
SELECT
  lifecycle
FROM
  hosts
WHERE
   name=%s;
'''
