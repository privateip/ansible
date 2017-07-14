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
module: ofs_l3_interface
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage logical Layer3 interfaces on FlexSwitch systems
description:
  - Logical layer3 interfaces are built on top of ports and/or logical
    interfaces and can be used to create logical netowrks.  This module
    can declaratively provision logical layer3 interfaces.
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
      - The reference name of the logical interface to configure and
        manage on the remote system.  This argument accepts a text
        value that represents the logical interface.
      - This argument is a config argument and will update the configuration
        of the remote system.
      - This argument is the reference identifier for uniquely identifying
        objects in FlexSwitch and is required either as an individual
        argument or in the aggregate.
    required: false
    default: null
  ipv4:
    description:
      - Configure the logical layer3 interface with the IPv4 address specified
        in this argument.  This argument accepts values in the format of
        address/masklen (A.B.C.D/E).
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  state:
    description:
      - Defines the desired state of the interface on the remote system.  This
        argument is used to specify the intended state of the logical layer3
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
    defaut: localhost
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
- name: create or update ipv4 logical interface
  ofs_l3_interface:
    name: fpPort1
    ipv4: 10.1.1.1/32

- name: remove ipv4 interface
  ofs_l3_interface:
    name: fpPort1
    state: absent
"""

RETURN = """
deleted:
  description: Returns the list of VLAN IDs that were deleted
  returned: always
  type: list
  sample: ['fpPort1', 'fpPort2']
added:
  description: Returns the list of VLAN IDs that were inserted
  returned: always
  type: list
  sample: ['fpPort1', 'fpPort2']
purged:
  description: Returns the list of VLAN IDs that were purged
  returned: always
  type: list
  sample: ['fpPort1', 'fpPort2']
updated:
  description: Returns the list of VLAN IDs that were updated
  returned: always
  type: list
  sample: ['fpPort1', 'fpPort2']
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def set_enabled(value):
    return 'UP' if value is True else 'DOWN'


def get_enabled(value):
    return value == 'UP'


def check_state(desired_value, current_value):
    if desired_value in ('up', 'down'):
        return desired_value == current_value
    return desired_value == 'present'


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(),
        enabled=dict(type='bool'),
        ipv4=dict(),

        delay=dict(type='int', default=10),
        state=dict(default='present', choices=['present', 'absent', 'up', 'down']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('name', 'IntfRef'),
        mapped_key('enabled', 'AdminState', get_enabled, set_enabled),
        mapped_key('ipv4', 'IpAddr'),
        mapped_key('state')
    ])

    state_keymap = frozenset([
        mapped_key('name', 'IntfRef'),
        mapped_key('state', 'OperState', lambda x: x.lower(), check=check_state)
    ])

    runner = Runner(module)

    runner.set_config_keymap(config_keymap)
    runner.set_state_keymap(state_keymap)

    runner.set_getter_url(make_url(module, 'config/IPv4Intfs'))
    runner.set_setter_url(make_url(module, 'config/IPv4Intf'))
    runner.set_state_url(make_url(module, 'state/IPv4Intfs'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('name')

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
