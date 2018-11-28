#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: net_interface
version_added: "2.8"
author: "Peter Sprygada (@privateip)"
short_description: Manage physical and logical interfaces
description:
  - Provide configuration management of both physical and logical interfaces
    on network devices.
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
  lookup_source:
    description:
      - Provides one or more source
        interfaces to use for performing DNS lookups.  The interface
        provided in C(lookup_source) must be a valid interface configured
        on the device.
  name_servers:
    description:
      - List of DNS name servers by IP address to use to perform name resolution
        lookups.  This argument accepts either a list of DNS servers See
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
"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: when connection type is C(network_cli)
  type: list
  sample:
    - hostname ios01
    - ip domain name test.example.com
"""
from ansible.module_utils._text import to_text
from ansible.module_utils.network.common.module import NetworkModule

import ansible.module_utils.network.eos.providers.cli.config.interfaces


def main():
    """main entry point for module execution
    """
    ipv4_spec = {
        'address': dict(),
        'masklen': dict()
    }

    switchport_spec = {
        'mode': dict(default='access', choices=['access', 'trunk']),
        'access_vlan': dict(type='int'),
        'trunk_native_vlan': dict(type='int'),
        'trunk_allowed_vlans': dict()
    }

    config_spec = {
        'name': dict(required=True),
        'description': dict(),
        'enabled': dict(type='bool'),
        'vrf': dict(),
        'ipv4': dict(type='dict', elements='dict', options=ipv4_spec),
        'switchport': dict(type='dict', elements='dict', options=switchport_spec),
    }

    argument_spec = {
        'config': dict(type='list', elements='dict', required=True, options=config_spec),
        'operation': dict(default='merge', choices=['merge', 'replace', 'override'])
    }

    module = NetworkModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    try:
        result = module.edit_config()
    except Exception as exc:
        module.fail_json(msg=to_text(exc))

    module.exit_json(**result)

if __name__ == '__main__':
    main()
