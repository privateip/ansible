#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
#
# This file is part of Ansible by Red Hat
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'core'}


DOCUMENTATION = """
---
module: ofs_policy
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage the aggregate set of policies configured in FlexSwitch
description:
  - Provides management of individual and/or the aggregate set
    of policies configured on a remote system running FlexSwitch
  - This module provides a set of arguments to configure the objects on
    the system.  Config arguments will perform configuration tasks in
    a declarative fashion
  - This module supports aggregates which can be used to configure an
    aggregate set of objects on the system.  Aggregate resources can also
    be purged.
  - This module provides a set of arguments to validate the current
    state of the objects on the system.  State arguments will validate the
    object state but not make changes to the system.
options:
  name:
    description:
      - The name of policy to be present or absent from the FlexSwitch
        configuration.  This argument accepts a text value that uniquely
        identifies the policy name.
      - This argument is a config argument and will update the configuration
        of the remote system.
      - This argument is the reference identifier for uniquely identifying
        objects in FlexSwitch and is required either as an individual
        argument or in the aggregate.
    required: false
    default: null
  match:
    description:
      - Configures the policy match value for the specified name policy
        in the remote system configuration.  This value accepts either
        C(all) or C(any)
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    choices: ['all', 'any']
  policy_type:
    description:
      - Configures the policy type to be configured on the remote system for
        the specified named policy.  The policy type value can be one of
        C(bgp), C(ospf) or C(all).
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    choices: ['bgp', 'ospf', 'all']
  priority:
    description:
      - Assigns a priority value to the specified name policy configured on
        the remote system.  This argument accepts an integer value to assign
        the priority setting in the configuration on the remote system.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  statements:
    description:
      - Configures the aggregate set of policy statements that comprise the
        specified name policy in the configuration of the remote system.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  aggregate:
    description:
      - Configures an aggregate set of VLAN objects on the remote system.
        This argument accepts a list of VLAN objects that support the
        module keys.
    required: false
    default: null
  delay:
    description:
      - If a configuration change is made to the system, this argument
        will cause the module to delay before attempting to check the state
        values.  The delay value is specified in seconds.  If no configuration
        change is made to the system, then the delay argument is not used
    required: false
    default: 10
  purge:
    description:
      - Used to purge existing VLAN IDs from the remote system unless
        the VLAN ID is explicitly configured for this module.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: false
    type: bool
  state:
    description:
      - Defines the desired state of the VLAN ID on the remote system.  This
        argument is used to specify the intended state of the VLAN
        object on the remote system
      - This argument is a state argument and will verify the state of
        the object on the remote system.
    required: false
    default: present
    choices: ['present', 'absent']
  api_host:
    description:
      - The destination host serving the FlexSwitch API on the remote
        system.  Normally this is the remote hostname of the system.  This
        argument accepts a hostname or IP address and is used to construct
        the API URL.
    required: false
    default: localhost
  api_port:
    description:
      - The destination port serving the FlexSwitch API on the remote
        system.  This argument accepts an integer value in the range
        of 1 to 65534 and is used to construct the API URL.
    required: false
    default: 8080
notes:
  - This module has been tested of FlexSwitch 1.1.0.24
"""

EXAMPLES = """
- name: add a single policy to the system
  ofs_policy:
    name: p1_match
    statements:
      - s1_permit
      - s2_permit

- name: remove a single policy from the system
  ofs_policy:
    name: p2_match
    state: absent

- name: remove all policies from the system
  ofs_policy:
    purge: yes

- name: configure the aggregate set of policies on the system
  ofs_policy:
    aggregate:
      - p1_match
      - p2_match_all
    state: present
"""

RETURN = """
deleted:
  description: Returns the list of policies that were deleted
  returned: always
  type: list
  sample: ['p1_match', 'p2_match_all']
added:
  description: Returns the list of polcies that were inserted
  returned: always
  type: list
  sample: ['p1_match', 'p2_match_all']
purged:
  description: Returns the list of policies that were purged
  returned: always
  type: list
  sample: ['p1_match', 'p2_match_all']
updated:
  description: Returns the list of policies that were updated
  returned: always
  type: list
  sample: ['p1_match', 'p2_match_all']
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def set_statements(value):
    objects = list()
    for item in value:
        if isinstance(item, Mapping):
            if 'statement' not in item:
                raise Exception('missing required key: statement')
            objects.append(item)
        else:
            objects.append({'Statement': item})
    return objects


def transform_statements(value):
    objects = list()
    for item in value:
        if isinstance(item, Mapping):
            if 'statement' not in item:
                raise Exception('missing required key: statement')
            if 'priority' not in item:
                item['priority'] = 0
            objects.append(item)
        else:
            objects.append({'statement': item, 'priority': 0})
    return objects


def get_statements(value):
    objects = list()
    for item in value:
        objects.append({
            'statement': item['Statement'],
            'priority': item['Priority']
        })
    return objects


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(),

        match=dict(choices=['any', 'all']),
        policy_type=dict(choices=['bgp', 'ospf', 'all']),

        priority=dict(type='int'),

        statements=dict(type='list'),

        aggregate=dict(type='list'),
        purge=dict(type='bool', default=False),

        state=dict(default='present', choices=['present', 'absent']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('name', 'Name'),
        mapped_key('match', 'MatchType'),
        mapped_key('policy_type', 'PolicyType'),
        mapped_key('priority', 'Priority'),
        mapped_key('statements', 'StatementList', get_statements, set_statements, transform_statements),
        mapped_key('state')
    ])


    runner = Runner(module)

    runner.set_config_keymap(config_keymap)

    runner.set_getter_url(make_url(module, 'config/PolicyDefinitions'))
    runner.set_setter_url(make_url(module, 'config/PolicyDefinition'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('name')

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
