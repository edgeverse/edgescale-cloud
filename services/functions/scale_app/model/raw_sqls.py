# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

count_all_store_apps_sql = 'SELECT count(*) FROM dcca_applications AS A WHERE A.logical_delete_flag IS FALSE AND A.in_store IS TRUE;'


query_app_id_store_sql = '''
SELECT
  A.id AS app_id, A.name, A.display_name, A.description,
  A.likes, A.stars, A.image, A.is_public, U.username
FROM
  dcca_applications AS A
LEFT JOIN dcca_users AS U
  ON A.owner_id = U.id
WHERE
  A.id=%s
  AND in_store = TRUE;
'''

count_app_owner_name_sql = '''
SELECT
  count(id)
FROM
  dcca_applications AS A
WHERE
  A.name=%s
  AND (A.owner_id=%s AND A.in_store=FALSE)
  AND A.logical_delete_flag=FALSE ;
'''

query_all_store_apps_sql = '''
SELECT
  A.id, A.name, A.display_name,
  A.description, A.likes, A.stars,
  A.image, A.is_public, U.username
FROM
  dcca_applications AS A
LEFT JOIN dcca_users AS U
  ON A.owner_id = U.id
WHERE
  A.logical_delete_flag=FALSE
  AND A.in_store IS TRUE
ORDER BY A.id DESC
LIMIT %s
OFFSET %s ;
'''

# Query softapps by app ID
query_softapps_sql = '''
SELECT
  S.id, S.version,
  S.mirror_id AS registry_id,
  S.image_name,
  S.commands, S.args,
  S.hostnetwork, S.ports,
  S.volumes, S.volume_mounts,
  S.cap_add, S.morepara
FROM
  dcca_softapps AS S
WHERE
  S.application_id=%s
'''

insert_softapp_sql_v0 = '''
INSERT INTO dcca_softapps
  (version, mirror_id, image_name, application_id, commands,
   args, hostnetwork, ports, volumes, volume_mounts, cap_add)
VALUES
  (%s, %s, %s, %s, %s,
   %s, %s, %s, %s, %s,
   %s)
RETURNING id;'''

insert_softapp_sql = '''
INSERT INTO dcca_softapps
  (version, mirror_id, image_name, application_id, commands,
   args, hostnetwork, ports, volumes, volume_mounts, cap_add, morepara)
VALUES
  (%s, %s, %s, %s, %s,
   %s, %s, %s, %s, %s,
   %s, %s)
RETURNING id;'''

select_softapp_sql = '''
SELECT
  S.id,
  AM.name AS mirror,
  S.image_name AS image,
  S.version AS version
FROM
  dcca_softapps AS S
LEFT JOIN
  dcca_app_mirror AS AM ON S.mirror_id = AM.id
LEFT JOIN
  dcca_applications AS APP ON S.application_id = APP.id
WHERE
  S.mirror_id=%s
  AND S.image_name=%s
  AND S.version=%s
  AND S.application_id=%s ;
'''

query_app_tags_sql = '''
SELECT
  T.id, T.name
FROM dcca_ass_app_tag AS AT, dcca_tags AS T
WHERE application_id=%s
  AND AT.tag_id=T.id ;
'''

# Insert one application record to the store
# ('{name}', '{display_name}', '{description}', {vendor_id}, '{image}', {is_public})
create_app_item_sql = '''
INSERT INTO dcca_applications
  (name, display_name, description, image, is_public, owner_id)
VALUES
  (%s, %s, %s, %s, %s, %s)
RETURNING id ;
'''

# Logical delete the app
logical_delete_app_sql = 'UPDATE dcca_applications SET logical_delete_flag=TRUE WHERE id=%s ;'


# Query application document
query_app_doc_sql = '''
SELECT
  documents
FROM
  dcca_applications
WHERE id=%s ;
'''

# Update APP document
update_app_doc_sql = '''
UPDATE
  dcca_applications AS A
SET
  documents=%s
WHERE id=%s ;
'''

# Query user name
query_name_sql = '''
SELECT username FROM dcca_users WHERE id=%s;
'''

# Query owner's app
count_app_owner_sql = '''
SELECT
  count(id)
FROM
  dcca_applications AS A
WHERE
  A.id=%s
  AND A.owner_id=%s
  AND A.logical_delete_flag=FALSE ;
'''

# Query owner's app
count_app_owner_include_store_sql = '''
SELECT
  count(id)
FROM
  dcca_applications AS A
WHERE
  A.id=%s
  AND (A.owner_id=%s OR A.in_store IS TRUE)
  AND A.logical_delete_flag=FALSE ;
'''

# Query if the app has a "in store" flag
count_app_in_store_sql = '''
SELECT
  count(id)
FROM
  dcca_applications AS A
WHERE
  A.id=%s
  AND A.logical_delete_flag IS FALSE
  AND A.in_store IS TRUE ;
'''

query_image_versions_sql = '''
SELECT
  version
FROM dcca_softapps
WHERE
  application_id=%s;
'''

query_app_by_id_sql = '''
SELECT
  A.id AS app_id, A.name, A.display_name, A.description,
  A.likes, A.stars, A.image, A.is_public, U.username
FROM
  dcca_applications AS A
LEFT JOIN dcca_users AS U
  ON A.owner_id = U.id
WHERE
  A.id=%s
  AND A.logical_delete_flag IS FALSE ;
'''

apply_app_sql = '''
INSERT INTO dcca_apply_apps (user_id, comments, app_id)  VALUES (%s, %s, %s);
'''

query_all_apply_items_sql = '''
SELECT
  R.id, U.username,
  A.name AS app_name,
  R.created_at, R.comments,
  R.approved, R.status
FROM
  dcca_apply_apps AS R
LEFT JOIN dcca_applications AS A
  ON R.app_id=A.id
LEFT JOIN dcca_users U
  ON R.user_id=U.id
{filter}
ORDER BY {order_by} {order_type}
LIMIT {limit} OFFSET {offset}
'''

count_total_apply_apps_sql = '''
SELECT
  count(R.id)
FROM
  dcca_apply_apps AS R
LEFT JOIN dcca_users AS U
  ON R.user_id=U.id
{filter}
'''

query_req_info_sql = '''
SELECT
  AY.app_id
FROM
  dcca_apply_apps AS AY
WHERE
  AY.id=%s ;
'''

update_apply_status_sql = '''
UPDATE
  dcca_apply_apps
SET
  approved=%s,
  status=%s
WHERE
  id=%s ;
'''

update_in_store_status_sql = '''
UPDATE
  dcca_applications
SET
  in_store=%s
WHERE
  id=%s ;
'''

# Query mirrors which special user can use
query_mirror_sql = '''
SELECT 
  id, name, is_public, description 
FROM 
  dcca_app_mirror;
'''

select_application_sql = '''
  select count(id) from dcca_applications WHERE id=%s;
'''

# Query the docker image
count_docker_image_sql = '''
SELECT
  count(SA.id)
FROM
  dcca_softapps AS SA
LEFT JOIN dcca_applications AS A
  ON SA.application_id=A.id
WHERE 
  A.owner_id=%s
  AND A.id=%s
  AND SA.id=%s
  AND A.logical_delete_flag=FALSE ;
'''

# Remove docker image
remove_docker_image_sql = 'DELETE FROM dcca_softapps WHERE id=%s RETURNING ID;'

query_application_tags_sql = '''
SELECT 
  A.id AS app_id,
  T.id AS tag_id,
  T.name AS tag_name
FROM
  dcca_applications AS A
LEFT JOIN dcca_ass_app_tag AS AT
  ON A.id=AT.application_id
LEFT JOIN dcca_tags AS T
  ON AT.tag_id=T.id
WHERE {conditions};
'''

query_tag_sql = '''
SELECT id FROM dcca_tags WHERE name='{name}';
'''

create_tag_sql = '''
INSERT INTO dcca_tags (name) VALUES ('{name}') RETURNING id;
'''

attach_tag_to_app_sql = '''
INSERT INTO 
  dcca_ass_app_tag
VALUES 
  ({app_id}, {tag_id})
ON CONFLICT
ON CONSTRAINT 
  dcca_ass_app_tag_application_id_tag_id_pk
DO NOTHING;
'''

remove_tag_from_app_sql = '''
DELETE FROM dcca_ass_app_tag 
WHERE 
  application_id={application_id} 
  AND tag_id=(SELECT id FROM dcca_tags WHERE name='{tag_name}');
'''

update_app_permission_sql = '''
UPDATE
  dcca_applications
SET
  is_public=%s
WHERE
  id=%s ;
'''
