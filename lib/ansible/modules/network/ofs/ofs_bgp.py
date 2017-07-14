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
module: ofs_bgp
version_added: "2.4"
author: "Peter Sprygada (@privateip)"
short_description: Manage the global BGP process on FlexSwitch
description:
  - Provide declarative management of the global BGP process running on
    FlexSwitch systems.  This module uses the FlexSwitch API to configure
    the set of parameters in thesystem.
  - This module provides a set of arguments to configure the objects on
    the system.  Config arguments will perform configuration tasks in
    a declarative fashion
  - This module provides a set of arguments to validate the current
    state of the objects on the system.  State arguments will validate the
    object state but not make changes to the system.
options:
  bgp_as:
    description:
      - The BGP autonomous system number to be configured for the global
        BGP process.  This argument accepts integer values in the valid
        BGP AS process range of 1 to 65535.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: no
    default: null
  router_id:
    description:
      - Configure the global BGP router-id value for the running process
        on FlexSwitch.  This argument accepts an IPv4 address to configure
        as the router-id.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: no
    default: null
  enabled:
    description:
      - Controls the administrative state of the global BGP process on the
        remote system.  When the value is set to true, the BGP process is
        administratively enabled and when the value is set to false, the
        BGP process is set to administratively disabled.
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
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: 30
  default_med:
    description:
      - Configures the BGP MultiExit Discriminator (MED) value for the global
        BGP process.  This argument accepts integer values and sets the
        MED parameter
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  ibgp_max_paths:
    description:
      - Configures the maximimum number of iBGP paths to install into the
        FlexSwitch routing table.  This argument accepts an integer value
        that defines the maximum number of paths to install.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  ebgp_max_paths:
    description:
      - Configures the maximimum number of eBGP paths to install into the
        FlexSwitch routing table.  This argument accepts an integer value
        that defines the maximum number of paths to install.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  enable_ecmp:
    description:
      - Controls whether or not the global BGP process will use Equal Cost
        MultiPath (ECMP) for prefixes.  When this value is configure to
        true, ECMP is enabled and when this value is configured to false,
        the use of ECMP is disabled.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    type: bool
  enable_ecmp_multi_as:
    description:
      - Controls whether or not the global BGP process will use Equal Cost
        MultiPath (ECMP) from multiple BGP autonomous systems for prefixes.
        When this value is configure to true, ECMP is enabled and when this
        value is configured to false, the use of ECMP is disabled.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    type: bool
  total_paths:
    description:
      - This state argument defines the total number of paths the global
        BGP process should report.  This value accepts any conditional
        argument to evaluate the state
      - This argument is a state argument and will verify the state of
        the object on the remote system.
    required: false
    default: null
  ipv4_prefixes:
    description:
      - This state argument defines the total number of IPv4 prefixes the
        global BGP process should report.  This value accepts any conditional
        argument to evaluate the state
      - This argument is a state argument and will verify the state of
        the object on the remote system.
    required: false
    default: null
  ipv6_prefixes:
    description:
      - This state argument defines the total number of IPv6 prefixes the
        global BGP process should report.  This value accepts any conditional
        argument to evaluate the state
      - This argument is a state argument and will verify the state of
        the object on the remote system.
    required: false
    default: null
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
- name: global enable bgp
  ofs_bgp:
    bgp_as: 65000
    enabled: yes
    router_id: 1.1.1.1

- name: validate state values
  ofs_bgp:
    total_paths: 0
    ipv4_prefixes: ge(1)

- name: disable bgp
  ofs_bgp:
    enabled: no
"""

RETURN = """
#
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key



def set_enabled(value):
    return not value


def get_enabled(value):
    return not value


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        bgp_as=dict(),

        router_id=dict(),
        enabled=dict(type='bool'),

        default_med=dict(type='int'),

        ibgp_max_paths=dict(type='int'),
        ebgp_max_paths=dict(type='int'),

        enable_ecmp=dict(type='bool'),
        enable_ecmp_multi_as=dict(type='bool'),

        total_paths=dict(),
        ipv4_prefixes=dict(),
        ipv6_prefixes=dict(),

        delay=dict(default=30),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('bgp_as', 'ASNum'),
        mapped_key('router_id', 'RouterId'),
        mapped_key('enabled', 'Disabled', get_enabled, set_enabled),
        mapped_key('default_med', 'DefaultMED'),
        mapped_key('ibgp_max_paths', 'IBGPMaxPaths'),
        mapped_key('ebgp_max_paths', 'EBGPMaxPaths'),
        mapped_key('enable_ecmp', 'UseMultiplePaths'),
        mapped_key('enable_ecmp_multi_as', 'EBGPAllowMultipleAS')
    ])

    state_keymap = frozenset([
        mapped_key('total_paths', 'TotalPaths'),
        mapped_key('ipv4_prefixes', 'Totalv4Prefixes'),
        mapped_key('ipv6_prefixes', 'Totalv6Prefixes')
    ])

    runner = Runner(module)

    runner.set_config_keymap(config_keymap)
    runner.set_state_keymap(state_keymap)

    runner.set_getter_url(make_url(module, 'config/BGPGlobal'))
    runner.set_setter_url(make_url(module, 'config/BGPGlobal'))
    runner.set_state_url(make_url(module, 'state/BGPGlobal'))

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
