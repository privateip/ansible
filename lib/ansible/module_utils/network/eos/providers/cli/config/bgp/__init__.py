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
# Redistribute and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributes of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributes in binary form must reproduce the above copyright notice,
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
from ansible.module_utils.network.common.providers import ConfigEntity
from ansible.module_utils.network.common.providers import Attribute
from ansible.module_utils.network.eos.config.bgp.network import BgpNetworkConfig
from ansible.module_utils.network.eos.config.bgp.neighbor import BgpNeighborConfig
from ansible.module_utils.network.eos.config.bgp.address_family import BgpAddressFamilyConfig
from ansible.module_utils.network.eos.config.bgp.redistribute import RedistributeConfig


class BgpConfig(ConfigEntity):

    _bgp_as = Attribute(type='int')
    _router_id = Attribute()
    _log_neighbor_changes = Attribute(type='bool')
    _address_family = Attribute(cls=BgpAddressFamilyConfig)
    _neighbors = Attribute(cls=BgpNeighborConfig)
    _networks = Attribute(cls=BgpNetworkConfig)
    _redistribute = Attribute(cls=RedistributeConfig)
    _state = Attribute(default='present', choices=['present', 'absent', 'replace'])

    def render(self, config=None, operation=None):
        commands = list()

        if self.bgp_as is None:
            raise ValueError("missing required attribute: bgp_as")

        context = 'router bgp %s' % self.bgp_as

        if self.state in ('absent', 'replace'):
            cmd = 'router bgp %s' % self.bgp_as
            if not config or cmd in config:
                commands.append('no %s' % cmd)

        if self.state in ('present', 'replace'):
            for attr in self._attributes:
                if getattr(self, attr) is not None:
                    meth = getattr(self, '_render_%s' % attr, None)
                    if meth:
                        resp = meth(config)
                        if resp:
                            if not commands:
                                commands.append(context)
                            commands.extend(to_list(resp))

        if commands:
            commands.append('exit')

        return commands

    def _render_router_id(self, config=None):
        cmd = 'router-id %s' % self.router_id
        if not config or cmd not in config:
            return cmd

    def _render_log_neighbor_changes(self, config=None):
        cmd = 'bgp log-neighbor-changes'

        if self.log_neighbor_changes is True:
            if config or cmd not in config:
                return cmd

        elif self.log_neighbor_changes is False:
            if config or cmd in config:
                return 'no %s' % cmd

    def _render_redistribute(self, config):
        return self.redistribute.render(config)

    def _render_networks(self, config):
        return self.networks.render(config)

    def _render_neighbors(self, config):
        """ generate bgp neighbor configuration
        """
        return self.neighbors.render(config)

    def _render_address_family(self, config):
        """ generate address-family configuration
        """
        commands = list()
        for entry in self.address_family:
            resp = entry.render(config)
            if resp:
                commands.extend(resp)
        return commands


