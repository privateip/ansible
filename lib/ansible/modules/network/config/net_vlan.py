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
module: net_vlan
version_added: "2.4"
author: "Ricardo Carrillo Cruz (@rcarrillocruz)"
short_description: Manage VLANs on network devices
description:
  - This module provides declarative management of VLANs
    on network devices.
options:
  config:
    description:
      - Provide the VLAN configurtion for the network device.  The
        configuration argument will be applied to the device active
        configuration based on the I(operation) argument.
    type: list
    suboptions:
      name:
        description:
          - The value of the VLAN ID
        required: True
      name:
        description:
          - The name of the VLAN ID
      status:
        description:
          - The status of the VLAN ID
        choices:
          - active
          - suspend
    version_added: "2.8"
    aliases:
      - aggregate
  operation:
    description:
      - Describes how to apply the configuration to the device.  When this
        value is set to C(merge), the config values are merged with the active
        configuration.  When this value is set to C(replace), all current
        values in the configuration are replace.  When this value is set to
        C(override), the entire VLAN configuration is implemented.
    choices:
      - merge
      - replace
      - override
    default: merge
    version_added: "2.8"
  name:
    description:
      - Name of the VLAN.
  vlan_id:
    description:
      - ID of the VLAN.
  interfaces:
    description:
      - List of interfaces the VLAN should be configured on.
  purge:
    description:
      - Purge VLANs not defined in the I(aggregate) parameter.
    default: no
  state:
    description:
      - State of the VLAN configuration.
    choices:
     - present
     - absent
     - active
     - suspend
"""

EXAMPLES = """
- name: configure VLAN ID and name
  net_vlan:
    vlan_id: 20
    name: test-vlan

- name: remove configuration
  net_vlan:
    state: absent

- name: configure VLAN state
  net_vlan:
    vlan_id:
    state: suspend

"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: when connection type is C(network_cli)
  type: list
  sample:
    - vlan 20
    - name test-vlan
"""
from ansible.module_utils._text import to_text
from ansible.module_utils.network.common.module import NetworkModule

import ansible.module_utils.network.eos.cli.config.vlans

def main():
    """main entry point for module execution
    """
    vlan_spec = {
        'vlan_id': dict(type='int', required=True),
        'name': dict(),
        'status': dict(choices=['active', 'suspend'])
    }

    argument_spec = {
        'config': dict(type='list', elements='dict', required=True,
                       suboptions=vlan_spec, aliases=['aggregate']),

        'operation': dict(default='merge', choices=['merge', 'replace', 'override']),

        'name': dict(removed_in_version='2.12'),
        'vlan_id': dict(type='int', removed_in_version='2.12'),
        'interfaces': dict(removed_in_version='2.12'),
        'purge': dict(type='bool', removed_in_version='2.12'),
        'state': dict(choices=['present', 'absent', 'active', 'suspend'],
                      removed_in_version='2.12')
    }

    module = NetworkModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    operation = 'merge'
    status = None

    # display message about ignoring interfaces argument
    if module.params['interfaces'] is not None:
        module.warn("As of Ansible 2.8, net_vlan no longer supports the use of "
                    "the interfaces argument and will ignore any values")

    # handle the converstion from state to status here.  The state argument has
    # been deprecated in Ansible 2.8 and should be removed in +4 releases.  The
    # configuration options have move to the status argument.
    if module.params['state'] in ('active', 'suspend'):
        status = module.params['state']
        module.warn("As of Ansible 2.8, net_vlan now supports setting the `status`"
                    " argument to either `active` or `suspend`.  Use of the `state`"
                    " argument is deprecated")

    elif module.params['state'] in ('present', 'absent'):
        module.warn("As of Ansible 2.8, net_vlan no longer supports setting the "
                    "configured state to `present` or `absent`.  Please use the "
                    "operation agument instead")

    # handle the conversion from purge to operation here.  This change was
    # introduced in Ansible 2.8 and the purge argument should be removed from
    # the module in +4 releases
    if module.params['purge'] is not None and module.params['operation'] is None:
        module.warn("As of Ansible 2.8, net_vlan now supports using the `operation`"
                    " argument instead of `purge`")

        if module.params['purge'] is True:
            operation = 'replace'
        elif module.params['purge'] in (False, None):
            operation = 'merge'
    elif module.params['operation'] is not None:
        operation = module.params['operation']

    if module.params['config']:
        objects = module.params['config']

        for o in list(objects):
            if o.get('name') is None and module.params['name']:
                o['name'] = module.params['name']
            if o.get('status') and status:
                o['status'] = status

    else:
        module.warn("As of Ansible 2.8, net_vlan introduced the `config` argument "
                    "for applying device configuration.  The use of top level "
                    "arguments should be considered deprecated and playbooks should "
                    "be refactored to use the new argument instead")

        objects = [{
            'vlan_id': module.params['vlan_id'],
            'name': module.params['name'],
            'status': status
        })

    module.params['config'] = objects

    try:
        result = module.edit_config(resource, operation=operation)
    except Exception as exc:
        module.fail_json(msg=to_text(exc))

    module.exit_json(**result)

if __name__ == '__main__':
    main()
