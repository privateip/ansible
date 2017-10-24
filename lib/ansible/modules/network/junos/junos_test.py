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
module: junos_facts
version_added: "2.1"
author: "Nathaniel Case (@qalthos)"
short_description: Collect facts from remote devices running Juniper Junos
description:
  - Collects fact information from a remote device running the Junos
    operating system.  By default, the module will collect basic fact
    information from the device to be included with the hostvars.
    Additional fact information can be collected based on the
    configured set of arguments.
extends_documentation_fragment: junos
options:
  gather_subset:
    description:
      - When supplied, this argument will restrict the facts collected
        to a given subset.  Possible values for this argument include
        all, hardware, config, and interfaces.  Can specify a list of
        values to include a larger subset.  Values can also be used
        with an initial C(M(!)) to specify that a specific subset should
        not be collected. To maintain backward compatbility old style facts
        can be retrieved using all value, this reqires junos-eznc to be installed
        as a prerequisite.
    required: false
    default: "!config"
    version_added: "2.3"
  config_format:
    description:
      - The I(config_format) argument specifies the format of the configuration
         when serializing output from the device. This argument is applicable
         only when C(config) value is present in I(gather_subset).
         The I(config_format) should be supported by the junos version running on
         device.
    required: false
    default: text
    choices: ['xml', 'set', 'text', 'json']
    version_added: "2.3"
requirements:
  - ncclient (>=v0.5.2)
notes:
  - Ensure I(config_format) used to retrieve configuration from device
    is supported by junos version running on device.
  - With I(config_format = json), configuration in the results will be a dictionary(and not a JSON string)
  - This module requires the netconf system service be enabled on
    the remote device being managed.
  - Tested against vSRX JUNOS version 15.1X49-D15.4, vqfx-10000 JUNOS Version 15.1X53-D60.4.
"""

EXAMPLES = """
- name: collect default set of facts
  junos_facts:

- name: collect default set of facts and configuration
  junos_facts:
    gather_subset: config
"""

RETURN = """
ansible_facts:
  description: Returns the facts collect from the device
  returned: always
  type: dict
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection

def main():
    """ Main entry point for AnsibleModule
    """
    argument_spec = dict()

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    connection = Connection(module._socket_path)

    cap = connection.get_capabilities()
    cfg = connection.get_config()

    result = {'config': cfg, 'capabilities': cap}
    module.exit_json(**result)


if __name__ == '__main__':
    main()
