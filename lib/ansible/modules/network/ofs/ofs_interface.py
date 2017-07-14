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
module: ofs_interface
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage the aggregate set of logical interfaces
description:
  - Logical interfaces (namely Loopback interfaces) can be declaratively
    provisioned using this module.
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
  aggregate:
    description:
      - Configures an aggregate set of interface objects on the remote system.
        This argument accepts a list of interface objects that support the
        module keys.
    required: false
    default: null
  purge:
    description:
      - Used to purge existing interfaces from the remote system unless
        the interface name is explicitly configured for this module.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: false
    type: bool
  state:
    description:
      - Defines the desired state of the interface on the remote system.  This
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
- name: configure loopback interface
  ofs_interface:
    name: Loopback1
    state: present
    purge: yes

- name: configure multiple interfaces
  aggregate:
    - Loopback1
    - Loopback2
    - Loopback3

- name: remove all interfaces
  ofs_interface:
    purge: yes
"""

RETURN = """
deleted:
  description: Returns the list of logical interface names that were deleted
  returned: always
  type: list
  sample: ["Loopback1", "Loopback2"]
added:
  description: Returns the list of logical interface names that were added
  returned: always
  type: list
  sample: ["Loopback1", "Loopback2"]
purged:
  description: Returns the list of logical loopback names that were purged
  returned: always
  type: list
  sample: ["Loopback1", "Loopback2"]
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(),

        aggregate=dict(type='list'),
        purge=dict(type='bool', default=False),

        state=dict(default='present', choices=['present', 'absent']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    mutually_exclusive = [('name', 'aggregate')]

    module = AnsibleModule(argument_spec=argument_spec,
                           mutually_exclusive=mutually_exclusive,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('name', 'Name'),
        mapped_key('state')
    ])

    runner = Runner(module)

    runner.set_config_keymap(config_keymap)

    runner.set_getter_url(make_url(module, 'config/LogicalIntfs'))
    runner.set_setter_url(make_url(module, 'config/LogicalIntf'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('name')

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
