"""
Copyright 2019 Red Hat, Inc.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
from typing import Tuple

from management.role.model import Role
from migration_tool.models import V1group, V1permission, V1resourcedef, V1role


def aggregate_v1_role(role: Role) -> V1role:
    """
    Aggregate the role's access and policy as a consolidated V1role object.

    This maps the RBAC model to preloaded, navigable objects with the key data broken down.
    """
    perm_res_defs: dict[Tuple[str, str], list[V1resourcedef]] = {}
    default_perm_list: list[str] = []
    role_id = str(role.uuid)

    # Determine v1 permissions
    for access in role.access.all():
        default = True
        for resource_def in access.resourceDefinitions.all():
            default = False
            attri_filter = resource_def.attributeFilter
            # Some malformed data in db
            if attri_filter["operation"] == "in":
                if not isinstance(attri_filter["value"], list):
                    attri_filter["operation"] = "equal"
                elif attri_filter["value"] == [] or attri_filter["value"] == [None]:
                    continue
            res_def = V1resourcedef(attri_filter["key"], attri_filter["operation"], json.dumps(attri_filter["value"]))
            if res_def.resource_id != "":
                # TODO: Need to bind against "ungrouped hosts" for inventory
                add_element(perm_res_defs, (role_id, access.permission.permission), res_def)
        if default:
            default_perm_list.append(access.permission.permission)

    v1_perms = []
    for perm in default_perm_list:
        perm_parts = perm.split(":")
        v1_perm = V1permission(perm_parts[0], perm_parts[1], perm_parts[2], frozenset())
        v1_perms.append(v1_perm)

    for (role_id, perm), res_defs in perm_res_defs.items():
        perm_parts = perm.split(":")
        v1_perm = V1permission(perm_parts[0], perm_parts[1], perm_parts[2], frozenset(res_defs))
        v1_perms.append(v1_perm)

    # With the replicated role bindings algorithm, role bindings are scoped by group, so we need to add groups
    # TODO: We don't need to care about principals here – see RHCLOUD-35039
    # Maybe not even groups? See RHCLOUD-34786
    groups = set()
    for policy in role.policies.all():
        principals = [str(principal) for principal in policy.group.principals.values_list("uuid", flat=True)]
        groups.add(V1group(str(policy.group.uuid), frozenset(principals)))

    return V1role(role_id, frozenset(v1_perms), frozenset(groups))


def add_element(dict, key, value):
    """Add append value to dictionnary according to key."""
    if key not in dict:
        dict[key] = []
    dict[key].append(value)
