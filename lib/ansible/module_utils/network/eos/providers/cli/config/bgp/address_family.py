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


class BgpAddressFamily(ConfigEntity):

    _name = Attribute(required=True, choices=['ipv4', 'ipv6', 'vpnv4']),
    _vrf = Attribute(),
    _neighbors = Attribute(type='list'),
    _redistribute = Attribute(type='list'),

    def render(self, config=None):
        commands = list()

        context = 'address-family %s' % self.name
        if self.vrf:
            context += ' vrf %s' % self.vrf

        if config:
            section = ['router bgp %s' % bgp_as, context]
            config = self.get_section(config, section, indent=3)

        subcommands = list()
        for attr in self.argument_spec:
            if getattr(self, attr) is not None:
                meth = getattr(self, '_render_%s' % attr, None)
                if meth:
                    resp = meth(config)
                    if resp:
                        subcommands.extend(to_list(resp))

        if subcommands:
            commands = [context]
            commands.extend(subcommands)
            commands.append('exit-address-family')
        elif not config or context not in config:
            commands.extend([context, 'exit-address-family'])

        return commands

    def _render_neighbors(self, config=None):
        commands = list()
        for entry in self.neighbors:
            nbr = BgpNeighbor(**entry)
            resp = nbr.render(config)
            if resp:
                commands.extend(resp)
        return commands

    def _render_redistribute(self, config):
        commands = list()
        for entry in self.redistribute:
            redis = BgpRedistribute(**entry)
            resp = redis.render(config)
            if resp:
                commands.append(resp)
        return commands


class BgpAddressFamilyConfig(CollectionEntity):

    __item_class__ = BgpAddressFamily

    def render(self, config=None, operation=None):
        commands = list()

        for entry in itervalues(self.items):
            resp = entry.render(config)
            if resp:
                commands.append(resp)

        return commands
