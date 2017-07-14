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
short_description: Manage the set of BGP neighbors on FlexSwitch systems
description:
  - Provides configure and state management of individual and/or the
    aggregate set of BGP neighbors the system is connected to.  This module
    uses the FlexSwitch API to configure the BGP neighbors.
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
  neighbor:
    description:
      - Identifies the unique BGP neighbor connection to configure.  This
        value accepts a valid IPv4 address that specifies the BGP
        neighbor connection.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  remote_as:
    description:
      - Configures the BGP remote autonomous system number for the
        specified BGP neighbor connection.  This argument accepts integer
        values in the valid range of 1 to 65535.
    required: false
    default: null
  update_source:
    description:
      - Configures the BGP neighbor update source value for the specified
        BGP neighbor.  This argument accepts an IPv4 address that is used
        to set the update source for the neighbor connection.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  enabled:
    description:
      - Controls the administrative state of the BGP neighbor on the remote
        system.  When the value is set to true, the BGP neighbor is
        administratively enabled and when the value is set to false, the
        BGP neighbor is set to administratively disabled.
      - This argument is a config argument and will update the configuration
        of the remote system.
      - This argument is the reference identifier for uniquely identifying
        objects in FlexSwitch and is required either as an individual
        argument or in the aggregate.
    required: false
    default: null
    type: bool
  description:
    description:
      - Configures an arbitrary description for the specified BGP
        neighbor connection.  This argument accepts a text string
        to configure the neighbor description value.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  connect_retry_timer:
    description:
      - Configures the BGP neighbor connection retry timer setting
        for the specified neighbor connection.  This argument accepts
        integer values for configuring the neighbor value.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  keepalive_timer:
    description:
      - Configures the BGP neighbor keepalive timer setting for the
        specified neighbor connection.  This argument accepts integer
        values for configuring the neighbor keepalive timer value.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  hold_time:
    description:
      - Configures the BGP neighbor hold time value for the specific
        neighbor connection.  This argument accepts integer values for
        configuring the hold time parameter
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  local_as:
    description:
      - Configures the BGP neighbor local autonomous system value for
        the connection.  This argument accepts integer values in the
        valid BGP AS range of 1 to 65535.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
  next_hop_self:
    description:
      - Enables or disable the BGP neighbor next hop self attribute for
        the specified neighbor connection.  When set to true, next hop
        self is enabled and when set to false, next hop self is disabled.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: null
    type: bool
  aggregate:
    description:
      - Configures an aggregate set of BGP neighbors on the remote system.
        This argument accepts a list of BGP neighbors that support the
        module keys.
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
  purge:
    description:
      - Used to purge existing BGP neighbors from the remote system unless
        the BGP neighbor is explicitly configured for this module.
      - This argument is a config argument and will update the configuration
        of the remote system.
    required: false
    default: false
    type: bool
  state:
    description:
      - Defines the desired state of the BGP neighbor on the remote system.
        This argument is used to specify the intended state of the BGP
        neighbor on the remote system
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
- name: configure single bgp neigbor
  ofs_neighbor:
    neighbor: 1.1.1.1
    remote_as: 65000
    enabled: yes

- name: configure aggregate set of neighbors
  ofs_neighbor:
    aggregate:
      - 1.1.1.1
      - 2.2.2.2
    remote_as: 65000
    enabled: yes

- name: remove a single neighbor
  ofs_neighbor:
    neighbors 3.3.3.3
    state: absent
"""

RETURN = """
deleted:
  description: Returns the list of VLAN IDs that were deleted
  returned: always
  type: list
  sample: ['1.1.1.1', '2.2.2.2', '3.3.3.3']
added:
  description: Returns the list of VLAN IDs that were inserted
  returned: always
  type: list
  sample: ['1.1.1.1', '2.2.2.2', '3.3.3.3']
purged:
  description: Returns the list of VLAN IDs that were purged
  returned: always
  type: list
  sample: ['1.1.1.1', '2.2.2.2', '3.3.3.3']
updated:
  description: Returns the list of VLAN IDs that were updated
  returned: always
  type: list
  sample: ['1.1.1.1', '2.2.2.2', '3.3.3.3']
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ofs import Runner, make_url, mapped_key


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        neighbor=dict(),

        remote_as=dict(),
        update_source=dict(),
        enabled=dict(type='bool'),

        description=dict(),

        connect_retry_timer=dict(type='int'),
        keepalive_timer=dict(type='int'),
        hold_time=dict(type='int'),

        local_as=dict(),
        next_hop_self=dict(type='bool'),

        aggregate=dict(type='list'),
        purge=dict(type='bool', default=False),

        state=dict(default='present', choices=['present', 'absent']),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    config_keymap = frozenset([
        mapped_key('neighbor', 'NeighborAddress'),
        mapped_key('remote_as', 'PeerAS'),
        mapped_key('update_source', 'UpdateSource'),
        mapped_key('enabled', 'Disabled', lambda x: not x),
        mapped_key('description', 'Description'),
        mapped_key('connect_retry_timer', 'ConnectRetryTimer'),
        mapped_key('keepalive_timer', 'KeepaliveTime'),
        mapped_key('hold_time', 'HoldTime'),
        mapped_key('next_hop_self', 'NextHopSelf'),
        mapped_key('state')
    ])


    runner = Runner(module)

    runner.set_config_keymap(config_keymap)

    runner.set_getter_url(make_url(module, 'config/BGPv4Neighbors'))
    runner.set_setter_url(make_url(module, 'config/BGPv4Neighbor'))

    runner.set_static_map({'state': 'present'})
    runner.set_reference_key('neighbor')

    result = runner.run()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
