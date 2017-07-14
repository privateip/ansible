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
module: ofs_lldp
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage global LLDP settings
description:
  - Perform declarative management of global LLDP settings on systems
    running SnapRoute FlexSwitch.  This module uses the API to configure
    the global LLDP object on the system.
  - This module provides a set of arguments to configure the objects on
    the system.  Config arguments will perform configuration tasks in
    a declarative fashion
  - This module provides a set of arguments to validate the current
    state of the objects on the system.  State arguments will validate the
    object state but not make changes to the system.
options:
  enabled:
    description:
      - Adminstratively configure the LLDP procotol globally on the
        system.  Setting this value to true will globally enabled the
        protocol and setting this value to false will globally disable
        the protocol
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    type: bool
  mode:
    description:
      - Manages the operating mode of the LLPD protocol when it is enabled
        on the remote system.  This argument supports three valid choices.
        When it is configured as C(rx), then the system will only receive
        LLDP frames.  When it is conifugred as C(tx), then the system will
        only transmit LLDP frames.  When it is configured as C(both), the
        system will transmit and receive LLDP frames.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    choices: ['rx', 'tx', 'both']
  tx_interval:
    description:
      - Configures the global LLDP retransmit interval which sets the
        number of seconds between transmission of LLDP frames.  This
        argument accepts integer values.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  neighbors:
    description:
      - Specifies the number of LLDP neighbors expected when the global
        LLDP protocol is enabled.
      - This argument is a state argument and will verify the state of
        the object on the remote system.  It accepts conditional statements
        as valid input.
    required: false
    default: null
  delay:
    description:
      - If a configuration change is made to the system, this argument
        will cause the module to delay before attempting to check the state
        values.  The delay value is specified in seconds.  If no configuration
        change is made to the system, then the delay argument is not used
    required: false
    default: 30
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
- name: globally enable the LLDP protocol
  ofs_lldp:
    enabled: yes

- name: configure LLDP mode and retransmit interval
  ofs_lldp:
    mode: rx
    tx_interval: 10

- name: validate number of LLDP neighbors after enabling
  ofs_lldp:
    enabled: yes
    neighbors: 4

- name: verify LLDP has at least two neighbors
  ofs_lldp:
    neighbors: min(2)
"""

RETURN = """
#
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def set_mode(value):
    modes = {'rx': 'RxOnly', 'tx': 'TxOnly', 'both': 'TxRx'}
    return modes[value]


def get_mode(value):
    modes = {'TxRx': 'both', 'TxOnly': 'tx', 'RxOnly': 'rx'}
    return modes[value]


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        enabled=dict(type='bool'),
        mode=dict(choices=['tx', 'rx', 'both']),
        tx_interval=dict(type='int'),

        neighbors=dict(),

        delay=dict(type='int', default=30),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('enabled', 'Enable'),
        mapped_key('mode', 'TxRxMode', get_mode, set_mode),
        mapped_key('tx_interval', 'TransmitInterval')
    ])

    state_keymap = frozenset([
        mapped_key('neighbors', 'Neighbors')
    ])

    runner = Runner(module)

    runner.set_config_keymap(config_keymap)
    runner.set_state_keymap(state_keymap)

    runner.set_getter_url(make_url(module, 'config/LLDPGlobal'))
    runner.set_setter_url(make_url(module, 'config/LLDPGlobal'))
    runner.set_state_url(make_url(module, 'state/LLDPGlobal'))

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
