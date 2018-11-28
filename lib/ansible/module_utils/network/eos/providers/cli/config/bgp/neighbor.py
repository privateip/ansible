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
from ansible.module_utils.six import itervalues
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import ConfigEntity, CollectionEntity
from ansible.module_utils.network.common.providers import Attribute


class BgpNeighbor(ConfigEntity):

    _neighbor = Attribute(required=True)
    _activate = Attribute(type='bool')
    _description = Attribute()
    _enabled = Attribute(type='bool')
    _remote_as = Attribute(type='int')
    _send_community = Attribute(choices=['both']),
    _state = Attribute(default='present', choices=['present', 'absent', 'replace'])

    def render(self, config=None):
        commands = list()

        if self.state in ('absent', 'replace'):
            cmd = 'neighbor %s' % self.neighbor
            if not config or cmd in config:
                commands = ['no %s' % cmd]

        elif self.state in ('present', 'replace'):
            for attr in self._attributes:
                if getattr(self, attr) is not None:
                    meth = getattr(self, '_render_%s' % attr, None)
                    if meth:
                        commands.extend(to_list(meth(config)))

        return commands

    def _render_activate(self, config=None):
        cmd = 'neighbor %s activate' % self.neighbor
        if not config or cmd not in config:
            return cmd

    def _render_description(self, config=None):
        cmd = 'neighbor %s description %s' % (self.neighbor, self.description)
        if not config or cmd not in config:
            return cmd

    def _render_enabled(self, config=None):
        cmd = 'neighbor %s shutdown' % self.neighbor
        if self.enabled is False:
            cmd = 'no %s' % cmd
        if not config or cmd not in config:
            return cmd

    def _render_remote_as(self, config=None):
        cmd = 'neighbor %s remote-as %s' % (self.neighbor, self.remote_as)
        if not config or cmd not in config:
            return cmd

    def _render_send_community(self, config=None):
        cmd = 'neighbor %s send-community %s' % (self.neighbor, self.send_community)
        if not config or cmd not in config:
            return cmd

class BgpNeighborConfig(CollectionEntity):

    __item_class__ = BgpNeighbor
    __item_id__ = 'neighbor'

    def render(self, config=None, operation=None):
        commands = list()
        for entry in itervalues(self.items):
            resp = entry.render(config)
            if resp:
                commands.append(resp)
        return commands

    def _negate_neighbor(self, config, safe_list):
        commands = list()
        matches = re.findall('^\s{3}neighbor .*$', config, re.M)
        for match in matches:
            commands.apppend('no %s' % match)
        return commands
