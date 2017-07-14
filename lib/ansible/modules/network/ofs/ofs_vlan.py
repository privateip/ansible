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
module: ofs_vlan
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage the aggregate set of VLANs configure in FlexSwitch
description:
  - SnapRoute FlexSwitch supports configuration of VLAN objects via
    the API.  This module uses the API to configure the set of VLAN objects
    on the system.
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
  vlan_id:
    description:
      - The reference VLAN ID to configure on the remote system.  This
        argument accepts an integer value in the range of 1 to 4094.
      - This argument is a config argument and will update the configuration
        of the remote system.
      - This argument is the reference identifier for uniquely identifying
        objects in FlexSwitch and is required either as an individual
        argument or in the aggregate.
    required: false
    default: null
  aggregate:
    description:
      - Configures an aggregate set of VLAN objects on the remote system.
        This argument accepts a list of VLAN objects that support the
        module keys.
    required: false
    default: null
  enabled:
    description:
      - Controls the administrative state of the VLAN object on the remote
        system.  When the value is set to true, the VLAN object is
        administratively enabled and when the value is set to false, the
        VLAN object is set to administratively disabled.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    type: bool
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
    choices: ['present', 'absent', 'up', 'down']
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
- name: add a single vlan to the system
  ofs_vlan:
    vlan_id: 100
    state: present

- name: remove a vlan from the system
  ofs_vlan:
    vlan_id: 100
    state: absent

- name: configure aggregate set of vlans
  ofs_vlan:
    aggregate:
      - { vlan_id: 100, state: present }
      - { vlan_id: 101, state: absent }
    purge: yes

- name: add list of vlan ids with default values
  ofs_vlan:
    aggregate:
      - 100
      - 101
      - 102
    state: present
"""

RETURN = """
deleted:
  description: Returns the list of VLAN IDs that were deleted
  returned: always
  type: list
  sample: [100, 101, 102, 103]
added:
  description: Returns the list of VLAN IDs that were inserted
  returned: always
  type: list
  sample: [100, 101, 102, 103]
purged:
  description: Returns the list of VLAN IDs that were purged
  returned: always
  type: list
  sample: [100, 101, 102, 103]
updated:
  description: Returns the list of VLAN IDs that were updated
  returned: always
  type: list
  sample: [100, 101, 102, 103]
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def set_enabled(value):
    return 'UP' if value is True else 'DOWN'


def transform_state(val):
    return 'present' if val in ('present', 'up', 'down') else 'absent'


def check_state(desired_value, current_value):
    if desired_value in ('up', 'down'):
        return desired_value == current_value
    return desired_value == 'present'


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        vlan_id=dict(type='int'),

        enabled=dict(type='bool'),

        aggregate=dict(type='list'),
        purge=dict(type='bool', default=False),

        delay=dict(type='int', default=10),
        state=dict(default='present', choices=['present', 'absent', 'up', 'down']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('vlan_id', 'VlanId'),
        mapped_key('enabled', 'AdminState', lambda x: x == 'UP', set_enabled),
        mapped_key('state', None, transform_state)
    ])

    state_keymap = frozenset([
        mapped_key('vlan_id', 'VlanId'),
        mapped_key('state', 'OperState', lambda x: x.lower(), check=check_state)
    ])


    runner = Runner(module)

    runner.set_config_keymap(config_keymap)
    runner.set_state_keymap(state_keymap)

    runner.set_getter_url(make_url(module, 'config/Vlans'))
    runner.set_setter_url(make_url(module, 'config/Vlan'))
    runner.set_state_url(make_url(module, 'state/Vlans'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('vlan_id')

    result = runner.run()

    module.exit_json(**result)

if __name__ == '__main__':
    main()
