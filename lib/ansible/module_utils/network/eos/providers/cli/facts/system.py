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
from ansible.module_utils.network.eos.providers.facts import FactsProvider


@register_provider('eos', 'system')
class Facts(FactsProvider):
    """ Arista EOS System facts
    """

    def _set_hostname(self):
        output = self.cli("show hostname")
        match = re.search('Hostname:\s+(\S+)', output, re.M)
        self._resource.hostname = match.group(1) if match else None

    def _set_domain_name(self):
        output = self.cli('show hostname')
        match = re.search('FQDN:\s+(\S+)', output, re.M)
        self._resource.domain_name = match.group(1) if match else None

    def _set_system_mac(self):
        out = self.cli('show version')
        match = re.search('MAC address:s\s+(.+)', out, re.M)
        self._resource.system_mac = match.group(1) if match else None

    def _set_software_version(self):
        out = self.cli('show version')
        match = re.search('image version: (.+)', out, re.M)
        self._resource.software_version = match.group(1) if match else None

    def _set_total_memory(self):
        out = self.cli('show version')
        match = re.search('Total memory:\s+(\d+)', out, re.M)
        self._resource.total_memory = match.group(1) if match else None

    def _set_free_memory(self):
        out = self.cli('show version')
        match = re.search('Free memory:\s+(\d+)', out, re.M)
        self._resource.free_memory = match.group(1) if match else None
