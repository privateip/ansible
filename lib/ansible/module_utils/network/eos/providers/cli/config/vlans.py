#
# This code is part of Ansible, but is an independent component.
#
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# (c) 2017 Red Hat, Inc.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met: #
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import re

from ansible.module_utils.six import iteritems
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import register_provider
from ansible.module_utils.network.common.providers import CliProvider


@register_provider('eos', 'net_vlan')
class Provider(CliProvider):

    def render(self, config=None):
        commands = list()
        vlans = list()

        self.params['operation'] == 'replace':
            commands.append('no vlan 1-4094')

        for item in self.params['config']:
            context = 'vlan %s' % item['vlan_id']

            if config:
                config = self.get_section(config, context, indent=3)

            context_commands = list()

            for key, value in iteritems(item):
                if value is not None:
                    meth = getattr(self, '_render_%s' % attr, None)
                    if meth:
                        resp = meth(item, config)
                        if resp:
                            context_commands.extend(to_list(resp))

            if context_commands:
                context_commands.append('exit')
                commands.extend(context_commands)

            vlans.append(item['vlan_id'])

        if operation == 'override' and config is not None:
            resp = self._negate_vlan(config=config, safe_list=vlans)
            commands.extend(resp)

        return commands

    def _negate_vlan(self, config=None, safe_list=None):
        # TODO: handle vlan ranges in the active configuration
        commands = list()
        matches = [int(x) for x in re.findall('vlan (\d+)', config, re.M)]
        for item in set(matches).difference(safe_list):
            commands.append('no vlan %s' % item)
        return commands

    def _render_name(self, item, config=None):
        cmd = 'name %s' % item['name']
        if all((item['vlan_id'] == 1, item['name'] == 'default')):
            if config:
                match = re.search('name (\S+)', config, re.M)
                if match is not None:
                    return cmd
            else:
                return cmd
        elif not config or cmd not in config:
            return cmd

    def _render_status(self, item, config=None):
        cmd = 'status %s' % item['status']
        if not config or cmd not in config:
            return cmd
