# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

query_all_existing_tags_sql = '''
SELECT name FROM dcca_tags;
'''

query_tag_sql = '''
SELECT id FROM dcca_tags WHERE name='{name}';
'''

query_tags_sql = '''
SELECT id, name FROM dcca_tags WHERE name in (%s);
'''

create_tags_sql = '''
INSERT INTO dcca_tags (name) VALUES {names} RETURNING id;
'''

query_solution_tags_sql = '''
SELECT tag_id 
FROM
  dcca_ass_solution_tag 
WHERE
  solution_id={sol_id}
  AND tag_id in ({tag_ids}); 
'''

create_solution_tags_sql = '''
INSERT INTO dcca_ass_solution_tag
  (solution_id, tag_id)
VALUES
  {values}
RETURNING tag_id;
'''

remove_tag_from_solution_sql = '''
DELETE FROM dcca_ass_solution_tag
WHERE
  solution_id={sol_id}
  AND tag_id={tag_id};
'''
