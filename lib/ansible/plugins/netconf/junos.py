#
# (c) 2017 Red Hat Inc.
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
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import re

from xml.etree.ElementTree import fromstring

from ansible import constants as C
from ansible.module_utils._text import to_text
from ansible.errors import AnsibleConnectionFailure, AnsibleError
from ansible.plugins.netconf import NetconfBase
from ansible.plugins.netconf import ensure_connected

try:
    from ncclient import manager
    from ncclient.operations import RPCError
    from ncclient.transport.errors import SSHUnknownHostError
    from ncclient.xml_ import to_ele, to_xml, new_ele
except ImportError:
    raise AnsibleError("ncclient is not installed")


class Netconf(NetconfBase):

    def get_text(self, ele, tag):
        try:
            return to_text(ele.find(tag).text, errors='surrogate_then_replace').strip()
        except AttributeError:
            pass

    def get_device_info(self):
        device_info = {}

        device_info['network_os'] = 'junos'
        data = self.execute_rpc('get-software-information')
        reply = fromstring(data)
        sw_info = reply.find('.//software-information')

        device_info['network_os_version'] = self.get_text(sw_info, 'junos-version')
        device_info['network_os_hostname'] = self.get_text(sw_info, 'host-name')
        device_info['network_os_model'] = self.get_text(sw_info, 'product-model')

        return device_info

    @ensure_connected
    def execute_rpc(self, rpc):
        """RPC to be execute on remote device
           :rpc: Name of rpc in string format"""
        name = new_ele(rpc)
        if self._connection.transport == 'junos-eznc':
            return to_xml(self.m.rpc(name))
        else:
            return self.m.rpc(name).data_xml

    @ensure_connected
    def load_configuration(self, *args, **kwargs):
        """Loads given configuration on device
        :format: Format of configuration (xml, text, set)
        :action: Action to be performed (merge, replace, override, update)
        :target: is the name of the configuration datastore being edited
        :config: is the configuration in string format."""
        return self.m.load_configuration(*args, **kwargs).data_xml

    def get_capabilities(self):
        result = {}
        result['rpc'] = self.get_base_rpc() + ['commit', 'discard_changes', 'validate', 'lock', 'unlock', 'copy_copy']
        result['network_api'] = 'netconf'
        result['device_info'] = self.get_device_info()

        if self._connection.transport == 'junos-eznc':
            result['server_capabilities'] = [c for c in self.m._conn.server_capabilities]
            result['client_capabilities'] = [c for c in self.m._conn.client_capabilities]
            result['session_id'] = self.m._conn.session_id
        else:
            result['server_capabilities'] = [c for c in self.m.server_capabilities]
            result['client_capabilities'] = [c for c in self.m.client_capabilities]
            result['session_id'] = self.m.session_id
        return json.dumps(result)

    @ensure_connected
    def get_config(self, *args, **kwargs):
        """Retrieve all or part of a specified configuration.
           :source: name of the configuration datastore being queried
           :filter: specifies the portion of the configuration to retrieve
           (by default entire configuration is retrieved)"""
        if self._connection.transport == 'junos-eznc':
            return to_xml(self.m.rpc.get_config(*args, **kwargs))
        else:
            super(Netconf, self).get_config(*args, **kwargs)


