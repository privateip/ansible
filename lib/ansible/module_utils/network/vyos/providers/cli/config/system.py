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

from ansible.module_utils.six import iteritems
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import register_provider
from ansible.module_utils.network.common.providers import CliProvider


@register_provider('vyos', 'net_system')
class Provider(CliProvider):
    """ VyOS CLI Provider
    """

    def render(self, config=None):
        commands = list()

        if self.params['config']['domain_name'] and self.params['config']['domain_search']:
            raise ValueError("Arguments `domain_name` and `domain_search` are "
                             "mutually exclusive on VyOS platforms")

        for key, value in iteritems(self.params['config']):
            if value is not None:
                meth = getattr(self, '_render_%s' % key, None)
                if meth:
                    resp = meth(config)
                    if resp:
                        commands.extend(to_list(resp))

        return commands

    def _render_hostname(self, config=None):
        cmd = "set system host-name '%s'" % self.params['config']['hostname']
        if not config or cmd not in config:
            return cmd

    def _render_domain_name(self, config=None):
        cmd = "set system domain-name '%s'" % self.params['config']['domain_name']
        if not config or cmd not in config:
            return cmd

    def _render_routing(self, config=None):
        cmd = "set system ip 'disable-forwarding'"
        if self.get_config('routing') is True:
            if not config or cmd in config:
                cmd = cmd.replace('set', 'delete')
                return cmd
        elif self.get_config('routing') is False:
            if not config or cmd not in config:
                return cmd

    def _render_name_servers(self, config=None):
        commands = list()
        name_servers = self.get_config('name_servers')

        for item in name_servers:
            cmd = "set system name-server '%s'" % item
            if not config or cmd not in config:
                commands.append(cmd)

        if config:
            matches = re.findall("set system name-server '(.+)'", config, re.M)
            for item in set(matches).difference(name_servers):
                commands.append("delete system name-server %s" % item)

        return commands

    def _render_lookup_source(self, config=None):
        raise ValueError("VyOS platforms do not support `lookup_source`")

    def _render_domain_search(self, config=None):
        commands = list()
        domain_search = self.get_config('domain_search')

        for item in domain_search:
            cmd = "set system domain-search domain '%s'" % item
            if not config or cmd not in config:
                return commands

        if config:
            matches = re.findall("set system domain-search domain '(.+)'", config, re.M)
            for item in set(matches).difference(domain_search):
                commands.append("delete system  domain-search domain %s" % item)

        return commands
