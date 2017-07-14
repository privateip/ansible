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
module: ofs_policy_statement
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage the aggregate set of policy statements in FlexSwitch
description:
  - Manages individual and/or the aggregate set of policy statements
    confiugred on a system running FlexSwitch.  This module uses the
    FlexSwitch API to configure the policy statements.
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
      - Sets the unique name that identifies the policy statement in the
        configuration of the remote system.  This argument accepts a text
        value for the policy statement name.
      - This argument is a config argument and will update the configuration
        of the remote system.
      - This argument is the reference identifier for uniquely identifying
        objects in FlexSwitch and is required either as an individual
        argument or in the aggregate.
    required: false
    default: null
  action:
    description:
      - Configures the policy statement action value for the named policy
        statement.  When the action value is C(permit) the statement will
        pass and when the action value is C(deny) the statement will not pass.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    choices: ['permit', 'deny']
  match:
    description:
      - Configures the policy statement match value for the name policy
        statement.  This argument accepts one of two values C(all) or
        C(any).
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    choices: ['all', 'any']
  conditions:
    description:
      - Configures the specified name policy statement conditions on the
        remote system.
      - This argument is a config argument and will update the configuration
        of the remote system.
    require: false
    default: null
  aggregate:
    description:
      - Configures an aggregate set of VLAN objects on the remote system.
        This argument accepts a list of VLAN objects that support the
        module keys.
      - This argument is a config argument and will update the configuration
        of the remote system.
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
- name: configure a policy statement
  ofs_policy_statement:
    name: s1_permit
    action: permit

- name: remove a policy statement
  ofs_policy_statement:
    name: s1_permit
    state: absent

- name: configure an aggregate set of policy statements
  ofs_policy_statement:
    aggregate:
      - s1_permit
      - { name: s2_permit, action: deny }
    state: present
"""

RETURN = """
deleted:
  description: Returns the list of policy statements that were deleted
  returned: always
  type: list
  sample: ['s1_permit', 's2_permit', s3_permit']
added:
  description: Returns the list of policy statements that were inserted
  returned: always
  type: list
  sample: ['s1_permit', 's2_permit', s3_permit']
purged:
  description: Returns the list of policy statements that were purged
  returned: always
  type: list
  sample: ['s1_permit', 's2_permit', s3_permit']
updated:
  description: Returns the list of policy statements that were updated
  returned: always
  type: list
  sample: ['s1_permit', 's2_permit', s3_permit']
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(),
        match=dict(choices=['any', 'all']),
        action=dict(choices=['permit', 'deny']),
        conditions=dict(),

        aggregate=dict(type='list'),
        purge=dict(type='bool', default=False),

        state=dict(default='present', choices=['present', 'absent']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        ('name', 'Name'),
        ('match', 'MatchConditions'),
        ('action', 'Action'),
        ('conditions', 'Conditions'),
        ('state')
    ])

    runner = Runner(module)

    runner.set_config_keymap(config_keymap)

    runner.set_getter_url(make_url(module, 'config/PolicyStmts'))
    runner.set_setter_url(make_url(module, 'config/PolicyStmt'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('name')

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
