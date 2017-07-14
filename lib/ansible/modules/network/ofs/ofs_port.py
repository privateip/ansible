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
module: ofs_port
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage front panel physical ports
description:
  - SnapRoute FlexSwitch supports configuration of Port objects via
    the API.  This module uses the API to configure the front panel
    physical ports on the system.
  - This module provides a set of arguments to configure the objects on
    the system.  Config arguments will perform configuration tasks in
    a declarative fashion
  - This module provides a set of arguments to validate the current
    state of the objects on the system.  State arguments will validate the
    object state but not make changes to the system.
options:
  name:
    description:
      - The front panel physical port name as described and referenced
        in the system.  This argument accepts a string value that
        identifies the port to be managed.
      - This argument is a config argument and will update the configuration
        of the remote system.
      - This argument is the reference identifier for uniquely identifying
        objects in FlexSwitch and is required.
    required: true
    default: null
  description:
    description:
      - Assigns a readable description to the physical port on the
        remote system.  This argument accepts an arbitrary text string
        used to describe the physical port.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  mtu:
    description:
      - Modifies the Maximum Transmission Unit setting of the physical port
        on the remote system.  This argument accepts an integer value and
        assigns it to the MTU value of the port.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  enabled:
    description:
      - Controls the administrative state of the port object on the remote
        system.  When the value is set to true, the port object is
        administratively enabled and when the value is set to false, the
        port object is set to administratively disabled.
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
  state:
    description:
      - Defines the desired state of the physical port on the remote
        system.  This argument is used to specify the intended state
        of the physical port object on the remote system
      - This argument is a state argument and will verify the state of
        the object on the remote system.
    required: false
    default: null
    choices: ['up', 'down']
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
- name: configure port properties
  ofs_port:
    name: fpPort1
    description: Ansible test port
    enabled: yes

- name: verify port is operationally up
  ofs_port:
    name: fpPort1
    state: up
"""

RETURN = """
#
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def set_enabled(value):
    return 'UP' if value is True else 'DOWN'


def get_enabled(value):
    return value == 'UP'


def get_state(value):
    return value.lower()


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(required=True),

        description=dict(),
        mtu=dict(type='int'),

        enabled=dict(type='bool'),

        delay=dict(type='int', default=10),
        state=dict(default='up', choices=['up', 'down']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('name', 'IntfRef'),
        mapped_key('description', 'Description'),
        mapped_key('mtu', 'Mtu'),
        mapped_key('enabled', 'AdminState', get_enabled, set_enabled),
    ])

    state_keymap = frozenset([
        mapped_key('name', 'IntfRef'),
        mapped_key('state', 'OperState', get_state)
    ])

    runner = Runner(module)

    runner.set_config_keymap(config_keymap)
    runner.set_state_keymap(state_keymap)

    runner.set_getter_url(make_url(module, 'config/Ports'))
    runner.set_setter_url(make_url(module, 'config/Port'))
    runner.set_state_url(make_url(module, 'state/Ports'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('name')

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
