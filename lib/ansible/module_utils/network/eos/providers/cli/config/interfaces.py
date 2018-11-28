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
# are permitted provided that the following conditions are met:
#
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

from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import register_provider
from ansible.module_utils.network.common.providers import CliProvider


@register_provider('eos', 'net_interfaces')
class Provider(CliProvider):
    """Arista EOS interface config provider
    """

    def render(self, config=None):
        commands = list()
        safe_list = list()

        for item in self.params['config']:
            name = item['name'].capitalize()
            safe_list.append(name)

            context = 'interface %s' % name
            intfconfig = self.get_section(config, context, indent=3)

            if self.params['operation'] in ('override', 'replace'):
                if name[0:2].lower() == 'et':
                    commands.append('default %s' % context)
                elif name[0:2].lower() != 'ma':
                    commands.append('no %s' % context)

            subcommands = list()

            if item['switchport']:
                if item['ipv4']:
                    raise ValueError('ipv4 and switchport arguments are mutually exclusive')
                if item['vrf']:
                    raise ValueError('cannot assign switchport to a vrf')

            if item['description']:
                resp = self._render_description(item, intfconfig)
                if resp:
                    subcommands.extend(to_list(resp))

            vrf_changed = False

            if item['vrf']:
                resp = self._render_vrf(item, intfconfig)
                if resp:
                    vrf_changed = True
                    subcommands.append(resp)

            if item['ipv4'] or vrf_changed:
                resp = self._render_ipv4(item, intfconfig, vrf_changed)
                if resp:
                    subcommands.extend(to_list(resp))

            if item['switchport']:
                resp = self._render_switchport(item, intfconfig)
                if resp:
                    subcommands.extend(to_list(resp))

            if item['enabled'] is not None:
                resp = self._render_enabled(item, intfconfig)
                if resp:
                    subcommands.append(resp)

            if subcommands:
                commands.append(context)
                commands.extend(subcommands)
                commands.append('exit')

        if self.params['operation'] == 'override':
            resp = self._negate_config(config=config, safe_list=safe_list)
            if resp:
                commands.extend(resp)

        return commands

    def _render_description(self, item, config=None):
        cmd = 'description %s' % item['description']
        if not config or cmd not in config:
            return cmd

    def _render_enabled(self, item, config=None):
        if item['enabled'] is True:
            if not config or re.search('^\s{3}(shutdown)$', config, re.M) is not None:
                return 'no shutdown'
        elif item['enabled'] is False:
            if not config or re.search('^\s{3}(shutdown)$', config, re.M) is None:
                return 'shutdown'

    def _render_vrf(self, item, config=None):
        cmd = 'vrf forwarding %s' % item['vrf']
        if not config or cmd not in config:
            return cmd

    def _negate_config(self, config=None, safe_list=None):
        commands = list()
        matches = re.findall('^interface (.+)', config, re.M)
        for item in set(matches).difference(safe_list):
            if item[0:2].lower() not in ('et', 'ma'):
                commands.append('no interface %s' % item)
            if item[0:2].lower() == 'et':
                commands.append('default interface %s' % item)
        return commands

    def _render_ipv4(self, item, config=None, vrf_changed=False):
        commands = list()

        address = item['ipv4']['address']
        masklen = item['ipv4']['masklen']

        if config and 'no switchport' not in config:
            commands.append('no switchport')

        if vrf_changed or not all((address is None, masklen is None)):
            cmd = 'ip address %s/%s' % (address, masklen)
            if not config or cmd not in config:
                commands.append(cmd)

        return commands

    def _render_switchport(self, item, config=None):
        commands = list()

        params = item['switchport']

        if not config or 'ip address' in config:
            commands.append('no ip address')

        if not config or (config and 'no switchport' in config):
            commands.append('switchport')

        if not config:
            commands.append('switchport mode %s' % params['mode'])
        elif params['mode'] == 'access' and 'switchport mode trunk' in config:
            commands.append('switchport mode access')
        elif params['mode'] == 'trunk' and 'switchport mode trunk' not in config:
            commands.append('switchport mode trunk')

        cmd = 'switchport access vlan %s' % params['access_vlan']
        if not config or cmd not in config:
            commands.append(cmd)

        cmd = 'switchport trunk native vlan %s' % params['trunk_native_vlan']
        if not config or cmd not in config:
            commands.append(cmd)

        return commands
