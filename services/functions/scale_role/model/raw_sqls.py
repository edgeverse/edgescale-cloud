# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP


query_user_perm_sql = '''
SELECT 
  U.username, U.email, U.admin, U.display_name, U.account_type_id, T.name
FROM
  dcca_users AS U
LEFT JOIN dcca_account_types AS T
  ON U.account_type_id=T.id
WHERE 
  U.id=%s;
'''
