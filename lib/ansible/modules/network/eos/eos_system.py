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

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: eos_system
version_added: "2.3"
author: "Peter Sprygada (@privateip)"
short_description: Manage the system attributes on Arista EOS devices
description:
  - This module provides declarative management of node system attributes
    on Arista EOS devices.  It provides an option to configure host system
    parameters or remove those parameters from the device active
    configuration.
extends_documentation_fragment: eos
notes:
  - Tested against EOS 4.15
options:
  hostname:
    description:
      - Configure the device hostname parameter. This option takes an ASCII string value.
  domain_name:
    description:
      - Configure the IP domain name
        on the remote device to the provided value. Value
        should be in the dotted name form and will be
        appended to the C(hostname) to create a fully-qualified
        domain name.
  domain_search:
    description:
      - Provides the list of domain suffixes to
        append to the hostname for the purpose of doing name resolution.
        This argument accepts a list of names and will be reconciled
        with the current active configuration on the running node.
    aliases: ['domain_list']
  lookup_source:
    description:
      - Provides one or more source
        interfaces to use for performing DNS lookups.  The interface
        provided in C(lookup_source) can only exist in a single VRF.  This
        argument accepts either a list of interface names or a list of
        hashes that configure the interface name and VRF name.  See
        examples.
  name_servers:
    description:
      - List of DNS name servers by IP address to use to perform name resolution
        lookups.  This argument accepts either a list of DNS servers or
        a list of hashes that configure the name server and VRF name.  See
        examples.
  state:
    description:
      - State of the configuration
        values in the device's current active configuration.  When set
        to I(present), the values should be configured in the device active
        configuration and when set to I(absent) the values should not be
        in the device active configuration
    default: present
    choices: ['present', 'absent']
"""

EXAMPLES = """
- name: configure hostname and domain-name
  eos_system:
    hostname: eos01
    domain_name: test.example.com

- name: remove configuration
  eos_system:
    state: absent

- name: configure DNS lookup sources
  eos_system:
    lookup_source: Management1

- name: configure DNS lookup sources with VRF support
  eos_system:
      lookup_source:
        - interface: Management1
          vrf: mgmt
        - interface: Ethernet1
          vrf: myvrf

- name: configure name servers
  eos_system:
    name_servers:
      - 8.8.8.8
      - 8.8.4.4

- name: configure name servers with VRF support
  eos_system:
    name_servers:
      - { server: 8.8.8.8, vrf: mgmt }
      - { server: 8.8.4.4, vrf: mgmt }
"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: always
  type: list
  sample:
    - hostname eos01
    - ip domain-name test.example.com
session_name:
  description: The EOS config session name used to load the configuration
  returned: changed
  type: str
  sample: ansible_1479315771
"""
from ansible.module_utils.network.common.providers import NetworkModule
from ansible.module_utils._text import to_text
from ansible.module_utils.network.eos import eos_argument_spec
from ansible.module_utils.network.eos.config import system
from ansible.module_utils.network.eos.eapi import Eapi


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        hostname=dict(),

        domain_name=dict(),
        domain_list=dict(type='list', aliases=['domain_search']),

        # { interface: <str>, vrf: <str> }
        lookup_source=dict(type='list'),

        # { server: <str>; vrf: <str> }
        name_servers=dict(type='list'),

        state=dict(choices=['present', 'absent'], removed_in_version='2.8')
    )

    argument_spec.update(eos_argument_spec)

    module = NetworkModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    if module.params['state'] is not None:
        module.warn('eos_system `state` argument will be ignored')

    connection = None
    if module.params['provider'].get('transport') == 'eapi':
        connection = Eapi(module)

    try:
        result = module.execute_provider(connection=connection)
    except Exception as exc:
        module.fail_json(msg=to_text(exc))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
