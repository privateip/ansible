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


class Redistribution(ConfigEntity):

    _protocol = Attribute(required=True, choices=['static', 'connected'])
    _route_map = Attribute()

    def render(self, config=None):
        cmd = 'redistribute %s' % self.protocol

        if self.route_map:
            cmd += ' route-map %s' % self.route_map

        if not config or cmd not in config:
            return cmd

class RedistributeConfig(CollectionEntity):

    __item_class__ = Redistribution
    __item_id__ = 'protocol'

    def render(self, config=None, operation=None):
        commands = list()
        protocols = list()

        for entry in itervalues(self.items):
            resp = entry.render(config)
            if resp:
                commands.append(resp)
            protocols.append(entry.protocol)

        if operation == 'override' and config is not None:
            resp = self._negate_redistribute(config=config, safe_list=protocols)
            if resp:
                commands.append(resp)

        return commands

    def _negate_redistribute(self, config=None, safe_list=None):
        commands = list()
        for proto in ('connected', 'static'):
            if 'redistribute %s' % proto in config:
                commands.append('no redistirbute %s' % proto)
        return commands
