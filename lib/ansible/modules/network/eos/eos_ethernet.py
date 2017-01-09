#!/usr/bin/python
#
# This file is part of Ansible
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

DOCUMENTATION = """
---
module: eos_ethernet
version_added: "2.3"
author: "Peter Sprygada (@privateip)"
short_description: Manage physical Ethernet interfaces on EOS devices
description:
  - This module provides declarative management of the physical Ethernet
    interfaces on Arista EOS devices.  It allows playbooks configure
    interfaces and validate ephemeral state characteristics.
options:
  name:
    description:
      - The C(name) argument is used to specify the name of the interface
        to manage.  The C(name) argument accepts the full interface
        name of the interface to manage.
    required: true
  description:
    description:
      - The C(description) argument provides configuration management of
        the configured interface description.  The value accepts an
        ASCII string to configure on the interface.
    required: false
    default: null
  delay:
    description:
      - The C(delay) argument instructs the module to wait N seconds
        before attempting to validate state arguments if a change was
        made.  If no change as detected, the delay argument is ignored
        and the state arguments are checked immediately.
    required: false
    default: 10
  oper_status:
    description:
      - The C(oper_status) argument specifies the intended operational
        state of the interface.  This argument accepts values of either
        C(up) or C(down) that reflect the intended operational state of
        the interface in order for the task to pass.  If this value
        is not specified, the operational status of the interface is
        not evaluated.  See examples
    required: false
    choices: ['up', 'down']
    default: null
  neighbors:
    description:
      - The C(neighbors) argument provides a list of LLDP neighbors
        that are expected to be found on for the interface.  The value
        of neighbors can either be just a hostname of the intended
        neighbor or a list of hashes specifying the host and port.  If the
        port value is omitted, port connectivity is not checked.  If the
        C(neighbors) argument is not specified, LLDP neighbors are not
        evaluated.  See examples
    required: false
    default: null
  state:
    description:
      - Thec C(state) argument configures the administrative state of the
        physical Ethernet interface on the remote EOS device.  When the
        state is set to I(enabled) then the interface is administratively
        enabled and when the the stae is set to I(disabled), the interface
        is administratively disabled.
    required: false
    default: enabled
    choices: ['enabled', 'disabled']
"""

EXAMPLES = """
- name: configure Ethernet2
  eos_ethernet:
    name: Ethernet2
    description: test interface string
    state: enabled

- name: check Ethernet1 oper_status
  eos_ethernet:
    name: Ethernet2
    oper_status: up

- name: check Ethernet3 is connected to spine-01
  eos_ethernet:
    name: Ethernet3
    neighbors: spine-01

- name: configure Ethernet3 and check LLDP
  eos_ethernet:
    name: Ethernet3
    state: enabled
    neighbors:
      - host: spine-eos-02
        port: Ethernet2/1
"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: always
  type: list
  sample:
    - interface Ethernet2/1
    - description this is a test string
    - no shutdown
session_name:
  description: The EOS config session name used to load the configuration
  returned: when changed is True
  type: str
  sample: ansible_1479315771
start:
  description: The time the job started
  returned: always
  type: str
  sample: "2016-11-16 10:38:15.126146"
end:
  description: The time the job ended
  returned: always
  type: str
  sample: "2016-11-16 10:38:25.595612"
delta:
  description: The time elapsed to perform all operations
  returned: always
  type: str
  sample: "0:00:10.469466"
"""
import re
import time
import datetime

from ansible.module_utils.local import LocalAnsibleModule
from ansible.module_utils.eos2 import load_config, run_commands

def get_interface(module):
    name = module.params['name']

    cmd = 'show interfaces %s | json' % name
    data = run_commands(cmd)
    data = data[0]['interfaces'].get(name)

    if not data:
        module.fail_json(msg='interface %s not found' % name)

    return data

def map_obj_to_commands(want, have):
    commands = list()

    needs_update = lambda x: want.get(x) and (want.get(x) != have.get(x))

    if needs_update('description'):
        commands.append('description %s' % want['description'])

    if needs_update('state'):
        cmd = 'no shutdown' if want['state'] == 'enabled' else 'shutdown'
        commands.append(cmd)

    if commands:
        commands.insert(0, 'interface %s' % want['name'])

    return commands

def map_config_to_obj(module):
    data = get_interface(module)
    return {
        'name': module.params['name'],
        'state': 'disabled' if data['interfaceStatus'] == 'disabled' else 'enabled',
        'description': data['description']
    }

def do_state_checks(module, result):

    for key in ['oper_status', 'neighbors']:
        if module.params[key]:
            delay = module.params['delay']
            if result['changed'] and delay > 0:
                time.sleep(delay)
                break

    if module.params['oper_status']:
        data = get_interface(module)
        if data['lineProtocolStatus'] != module.params['oper_status']:
            module.fail_json(
                msg='oper_status wants %s, got %s' % \
                (module.params['oper_status'], data['lineProtocolStatus'])
            )

    if module.params['neighbors']:
        cmd = 'show lldp neighbors %s | json' % module.params['name']
        data = run_commands(cmd)
        data = data[0]['lldpNeighbors']

        neighbors = {}
        for item in data:
            host = item['neighborDevice']
            if host not in neighbors:
                neighbors[host] = list()
            neighbors[host].append(item['neighborPort'])

        for item in module.params['neighbors']:
            if not isinstance(item, dict):
                item = {'host': item, 'port': None}

            if item['host'] not in neighbors:
                module.fail_json(msg='host %s not found in neighbor list' % item['host'])

            ports = neighbors[item['host']]
            if item['port'] and item['port'] not in ports:
                module.fail_json(msg='port %s not found in neighbor ports list' % item['port'])

def validate_arguments(module):
    name = module.params['name']
    if not name.upper().startswith('ETH'):
        module.fail_json(msg='invalid interface name, got %s' % name)
    else:
        match = re.search('[a-zA-Z]+(.+)', name)
        module.params['name'] = 'Ethernet%s' % match.group(1)

def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(required=True),
        description=dict(),

        # intent arguments
        delay=dict(type='int', default=10),
        oper_status=dict(choices=['up', 'down']),
        # { host: <str>, port: <str> }
        neighbors=dict(type='list'),

        state=dict(default='enabled', choices=['enabled', 'disabled'])
    )

    module = LocalAnsibleModule(argument_spec=argument_spec,
                                supports_check_mode=True)

    validate_arguments(module)

    result = {'changed': False}

    want = module.params
    have = map_config_to_obj(module)

    commands = map_obj_to_commands(want, have)
    result['commands'] = commands

    if commands:
        commit = not module.check_mode
        response = load_config(module, commands, commit=commit)
        if response.get('diff') and module._diff:
            result['diff'] = {'prepared': response.get('diff')}
        result['session_name'] = response.get('session')
        result['changed'] = True

    do_state_checks(module, result)

    module.exit_json(**result)

