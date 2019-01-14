# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add missing roles for scope objects

Create Date: 2018-11-26 18:00:04.367674
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from collections import defaultdict

from alembic import op

from ggrc import db, utils
from ggrc.models import all_models
from ggrc.models.hooks.acl import propagation
from ggrc.migrations import utils as migrations_utils

# revision identifiers, used by Alembic.
revision = 'e3bbe8b7b0c9'
down_revision = 'dd2a3a987de5'


SCOPING_OBJECTS = [
    "AccessGroup",
    "DataAsset",
    "Facility",
    "Market",
    "Metric",
    "OrgGroup",
    "Process",
    "Product",
    "ProductGroup",
    "Project",
    "System",
    "Process",
    "TechnologyEnvironment",
    "Vendor",
]


ROLE_TYPES = [
    "Admin",
    "Assignee",
    "Verifier"
]


def _create_missing_acl():
  """Create missing acl"""
  # pylint: disable=protected-access
  propagation._add_missing_acl_entries()
  query = db.session.query(
      all_models.AccessControlList.id
  ).filter(
      all_models.AccessControlList.parent_id.is_(None)
  )
  all_acl_ids = [acl for acl, in query]
  for acl_ids in utils.list_chunks(all_acl_ids, chunk_size=50):
    propagation._delete_propagated_acls(acl_ids)
    propagation._set_empty_base_ids()
  return all_acl_ids


def _create_missing_acp():
  """Create missing acp"""
  all_acp = []
  for scope_object in SCOPING_OBJECTS:
    for role in ROLE_TYPES:
      role_id = db.session.query(
          all_models.AccessControlRole.id
      ).filter(
          all_models.AccessControlRole.name == role,
          all_models.AccessControlRole.object_type == scope_object
      ).first().id

      acp_data = db.session.query(
          all_models.AccessControlList
      ).outerjoin(
          all_models.AccessControlPerson
      ).filter(
          all_models.AccessControlList.ac_role_id == role_id,
          all_models.AccessControlPerson.id.is_(None)
      )

      persons = _get_persons(acp_data)
      for acp in acp_data:
        new_acp = all_models.AccessControlPerson(
            person_id=persons[(acp.object_type, acp.object_id)],
            ac_list_id=acp.id,
        )
        all_acp.append(new_acp)
        db.session.add(new_acp)
  db.session.commit()
  return [acp.id for acp in all_acp]


def _get_persons(acp_data):
  """Get persons for acp"""
  model_ids_map = defaultdict(list)
  persons = defaultdict(int)
  for acp in acp_data:
    model_ids_map[acp.object_type].append(acp.object_id)
  for key, value in model_ids_map.items():
    model = getattr(all_models, key)
    objs = model.query.filter(model.id.in_(value))
    for obj in objs:
      persons[(key, obj.id)] = obj.modified_by_id
  return persons


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  connection = op.get_bind()
  acl_ids = _create_missing_acl()
  if acl_ids:
    migrations_utils.add_to_objects_without_revisions_bulk(
        connection, acl_ids, 'AccessControlList'
    )
  acp_ids = _create_missing_acp()
  if acp_ids:
    migrations_utils.add_to_objects_without_revisions_bulk(
        connection, acp_ids, 'AccessControlPerson'
    )


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
