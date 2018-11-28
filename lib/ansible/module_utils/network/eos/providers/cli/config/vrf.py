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
from ansible.module_utils.six import iteritems
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import CliProvider
from ansible.module_tuils.network.common.providers import register_provider


@register_provider('eos', 'net_vrf')
class VrfConfig(CliProvider):

    def render(self, config=None, operation='merge'):
        commands = list()
        safe_list = list()

        context = 'vrf definition %s' % self.params['name']
        config = self.get_section(config, context, indent=3)

        if operation in ('override', 'replace'):
            commands.append('no %s' % context)

        if not config or context not in config:
            commands.append(context)

        for key, value in iteritems(self.params):
            if value is not None:
                meth = getattr(self, '_render_%s' % attr, None)
                if meth:
                    resp = meth(config)
                    if resp:
                        if not commands:
                            commands.append(context)
                    commands.extend(to_list(resp))

        if commands:
            commands.append('exit')

        if operation == 'override':
            self._negate_config(config, safe_list=safe_list)

        return commands

    def _render_description(self, config=None):
        cmd = 'description %s' % self.description
        if not config or cmd not in config:
            return cmd

    def _render_route_distinguisher(self, config=None):
        cmd = 'rd %s' % self.params['route_distinguisher']
        if not config or cmd not in config:
            return cmd
