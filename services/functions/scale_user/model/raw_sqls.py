# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

query_user_limit_by_uid_sql = '''
SELECT
  UL.limit_type_id,
  LT.name AS limit_type,
  UL.max_limit,
  UL.max_sec
FROM
  dcca_user_limits AS UL
LEFT JOIN dcca_user_limit_type AS LT
  ON UL.limit_type_id=LT.id
WHERE 
  UL.user_id=%s
ORDER BY UL.limit_type_id
LIMIT %s
OFFSET %s ;
'''

update_user_limit_sql = 'UPDATE dcca_user_limits SET max_limit=%s, max_sec=%s WHERE user_id=%s AND limit_type_id=%s ;'

query_all_types_sql = '''
SELECT 
  id, 
  name,
  "desc",
  default_max_limit,
  default_max_sec,
  is_per_time
FROM 
  dcca_user_limit_type ;
'''

query_limit_type_sql = '''
SELECT
  LT.id,
  LT.name,
  "desc",
  default_max_limit,
  default_max_sec,
  is_per_time
FROM
  dcca_user_limit_type AS LT
WHERE
  LT.id=%s ;
'''

query_user_id_sql = 'SELECT id FROM dcca_users WHERE username=%s ;'


query_one_user_sql = '''
SELECT 
  id, 
  username, 
  email,
  display_name,
  admin,
  created_at,
  update_at,
  timezone,
  image,
  status
FROM
  dcca_users
WHERE
  id=%s ;
'''

# The same columns as "query_all_users_filter_sql"
query_all_users_sql = '''
SELECT 
  id, username, email, display_name, admin, created_at, update_at, timezone, image, status
FROM
  dcca_users
ORDER BY id DESC 
limit %s offset %s;
'''

query_all_users_filter_sql = '''
SELECT 
  id, username, email, display_name, admin, created_at, update_at, timezone, image, status
FROM
  dcca_users
WHERE 
  username LIKE %s OR email LIKE %s
ORDER BY id DESC 
limit %s offset %s;
'''

count_all_user_cmd = '''
SELECT 
  count(id)
FROM
  dcca_users ;
'''

login_user_sql = '''
SELECT 
  id, 
  username, 
  password_hash, 
  password_salt, 
  admin,
  account_type_id,
  status
FROM 
  dcca_users
WHERE 
  username=%s;
'''

query_user_password_by_id_sql = '''
SELECT 
  id, 
  username, 
  password_hash, 
  password_salt, 
  admin,
  account_type_id,
  status
FROM 
  dcca_users
WHERE 
  id='{uid}';
'''

count_user_sql = '''SELECT count(id) FROM dcca_users WHERE username=%s'''
count_user_email_sql = '''SELECT count(id) FROM dcca_users WHERE email=%s;'''

create_user_sql = '''
INSERT INTO dcca_users 
(
  username, email, display_name, password_hash,
   password_salt, mail_enabled, timezone, account_type_id, oem_id
)
VALUES (
  %s, %s, NULL, %s, %s, %s, NULL, %s, %s
) RETURNING id;'''


update_user_by_id_sql = '''UPDATE dcca_users SET display_name=%s WHERE id=%s;'''
update_user_by_id_nullable_sql = '''UPDATE dcca_users SET display_name=%s, image=%s WHERE id=%s;'''

delete_user_by_name_sql = '''DELETE FROM dcca_users WHERE username=%s;'''

grant_user_default_role_sql = '''
INSERT INTO dcca_ass_user_role (user_id, role_id) VALUES (%s, %s);
'''

update_password_sql = 'UPDATE dcca_users SET password_hash=%s, password_salt=%s WHERE id=%s ;'

update_password_confirm_email_sql = '''
UPDATE 
  dcca_users 
SET 
  password_hash=%s, 
  password_salt=%s, 
  mail_enabled=TRUE
WHERE
  id=%s ;
'''

# Check if the username or email are correct
query_user_by_name_email_sql = '''
SELECT
  U.id,
  U.username,
  U.email
FROM
  dcca_users AS U
WHERE
  U.username=%s
  OR U.email=%s;
'''

# Query limits types
query_limit_types_sql = '''
SELECT 
  id, 
  name, 
  default_max_limit,
  default_max_sec
FROM
  dcca_user_limit_type;
'''

# Make the limits data
create_limits_sql = 'INSERT INTO dcca_user_limits (user_id, limit_type_id, max_limit, max_sec) VALUES (%s, %s, %s, %s);'


# Update user status
update_user_status = "UPDATE dcca_users SET status=%s WHERE id=%s;"


# Create solution certificate SQL
create_solution_cert_sql = '''
INSERT INTO dcca_certificates
  (body, private_key, chain, user_id)
VALUES (%s, %s, %s, %s) 
RETURNING id;
'''

query_solu_cert_sql = '''
SELECT 
  C.body,
  C.private_key,
  C.chain
FROM
  dcca_certificates AS C
WHERE 
  C.user_id=%s ;
'''

remove_solu_cert_sql = 'DELETE FROM dcca_certificates WHERE user_id=%s ;'

check_cert_exist_sql = 'SELECT count(id) FROM dcca_certificates WHERE user_id=%s ;'

query_account_types_sql = '''
SELECT 
  AT.id,
  AT.name
FROM
  dcca_account_types AS AT 
WHERE 
  AT.is_external IS TRUE;
'''

create_accounts_sql = '''
INSERT INTO dcca_accounts
 (company_name, telephone, email, job_title,
  account_type_id, first_name, last_name)
VALUES
 (%s, %s, %s, %s, %s, %s, %s)
 RETURNING id;
'''

count_email_sql = '''
SELECT
  count(id)
FROM
  dcca_accounts AS A
WHERE 
  A.email=%s;
'''

count_email_user_sql = '''
SELECT
  count(id)
FROM
  dcca_users AS U
WHERE 
  U.email=%s;
'''

update_accounts_sql = '''
UPDATE dcca_accounts
SET 
  status=%s 
WHERE 
  id=%s ;
'''

query_account_sql = '''
SELECT
  id, email, account_type_id
FROM
  dcca_accounts AS A
WHERE 
  A.id=%s ;
'''

count_oem_id_sql = '''
SELECT
  count(id)
FROM
  dcca_users AS A
WHERE
  A.oem_id='{}';
'''

query_oem_id_by_email = '''
SELECT
  oem_id
FROM
  dcca_users AS A
WHERE
  A.email=%s;
'''
