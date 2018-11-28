import re

from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import ConfigEntity
from ansible.module_utils.network.common.providers import Attribute


class MlagConfig(ConfigEntity):

    local_interface = Attribute()
    peer_address = Attribute()
    peer_link = Attribute()
    domain_id = Attribute()
    heartbeat_interval = Attribute()
    reload_delay = Attribute()
    enabled = Attribute(type='bool')
    state = Attribute(default='present', choices=['present', 'absent', 'replace'])

    def render(self, config=None, operation=None):
        commands = list()

        context = 'mlag configuration'

        if self.state == 'replace':
            config = None
        elif config is not None:
            config = self.getsection(config, context, indent=3)

        if self.state in ('absent', 'replace'):
            if not config or context in config:
                commands.append('no %s' % context)

        if self.state in ('present', 'replace'):
            subcommands = list()
            for attr in self._attributes:
                if getattr(self, attr) is not None:
                    meth = getattr(self, '_render_%s' % attr, None)
                    if meth:
                        resp = meth(config)
                        if resp:
                            if not subcommands:
                                subcommands.append(context)
                            subcommands.extend(to_list(resp))

            if subcommands:
                commands.extend(subcommands)
                commands.append('exit')

        return commands

    def parse(self, config):
        obj = {}
        config = self.getsection(config, 'mlag configuration')
        for attr in self._attributes:
            meth = getattr(self, '_parse_%s' % attr, None)
            if meth:
                obj.update(meth(config))
        obj['state'] = 'present' if config else 'absent'
        return obj

    def _parse_local_interface(self, config):
        match = re.search('local-interface (\S+)', config, re.M)
        return {'local_interface': match.group(1) if match else None}

    def _render_local_interface(self, config=None):
        if not self.local_interface.lower().startswith('vlan'):
            raise ValueError('local_interface must be Vlan')
        cmd = 'local-interface %s' % self.local_interface
        if not config or cmd not in onfig:
            return cmd

    def _parse_peer_address(self, config):
        match = re.search('peer-address (\S+)', config, re.M)
        return {'peer_address': match.group(1) if match else None}

    def _render_peer_address(self, config=None):
        cmd = 'peer-address %s' % self.peeraddress
        if not config or cmd not in config:
            return cmd

    def _parse_peer_link(self, config):
        match = re.search('peer-link (\S+)', config, re.M)
        return {'peer_link': match.group(1) if match else None}

    def _render_peer_link(self, config=None):
        cmd = 'peer-link %s' % self.peerlink
        if not config or cmd not in config:
            return cmd

    def _parse_domain_id(self, config):
        match = re.search('domain-id (\S+)', config, re.M)
        return {'domain_id': match.group(1) if match else None}

    def _render_domain_id(self, config=None):
        cmd = 'domain-id %s' % self.domainid
        if not config or cmd not in config:
            return cmd

    def _parse_heartbeat_interval(self, config):
        match = re.search('heartbeat-interval (\S+)', config, re.M)
        return {'heartbeat_interval': match.group(1) if match else None}

    def _render_heartbeat_interval(self, config=None):
        cmd = 'heartbeat-interval %s' % self.heartbeatinterval
        if not config or cmd not in config:
            return cmd

    def _parse_reload_delay(self, config=None):
        match = re.search('reload-delay (\S+)', config, re.M)
        return {'reload_delay': int(match.group(1)) if match else None}

    def _render_reload_delay(self, config=None):
        cmd = 'reload-delay %s' % self.reloaddelay
        if not config or cmd not in config:
            return cmd

    def _parse_enabled(self, config=None):
        return {'enabled': 'shutdown' in (config or '')}

    def _render_enabled(self, config=None):
        if self.enabled is True:
            if not config or 'shutdown' in config:
                return ['no shutdown']
        elif self.enabled is False:
            if not config or 'shutdown' not in config:
                return ['shutdown']
