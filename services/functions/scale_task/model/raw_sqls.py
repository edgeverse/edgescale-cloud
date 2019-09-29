# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

query_tasktmplt_list = '''
SELECT
  id, name, "desc", created_at, updated_at
FROM
  dcca_task_template
WHERE
  owner_id=%s AND name LIKE %s
ORDER BY updated_at DESC
LIMIT %s
OFFSET %s;
'''

query_tasktmplt_number_sql = '''
SELECT count(id) FROM dcca_task_template WHERE owner_id=%s AND name LIKE %s;
'''

query_one_tasktmplt_sql = '''
SELECT
  *
FROM
  dcca_task_template
WHERE
  owner_id=%s
  AND id = %s;
'''

create_tasktmplt_sql = '''
INSERT INTO dcca_task_template
  (name, "desc", owner_id, body)
VALUES
  (%s, %s, %s, %s)
RETURNING *;
'''

query_device_list_sql= '''
select 
  H.id,H.name,H.display_name,M.model,M.type,M.platform,M.vendor 
FROM hosts as H 
LEFT JOIN 
  dcca_models as M ON dcca_model_id=M.id 
where 
  H.owner_id=%s and H.id in %s;
'''

delete_tasktmplt_sql = '''
DELETE FROM dcca_task_template WHERE owner_id=%s AND id in %s RETURNING id;
'''

query_app_sql = '''
select 
  A.id, A.name, A.display_name, U.username, A.image, A.description 
FROM dcca_applications AS A
LEFT JOIN 
  dcca_users AS U ON A.owner_id = U.id
where 
 A.id=%s
'''
