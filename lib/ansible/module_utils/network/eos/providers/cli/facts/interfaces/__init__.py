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

from ansible.module_utils.six import itervalues
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.providers import ProviderBase
from ansible.module_utils.network.common.providers import Attribute
from ansible.module_utils.network.common.providers import register_provider


class Interface(ProviderBase):
    """ Arista EOS Interface facts
    """

    _name = Attribute()
    _description = Attribute()
    _enabled = Attribute(type='bool')
    _mtu = Attribute(type='int')

    def deserialize(self, obj):
        facts = {}
        for item in self._attributes:
            meth = getattr(self, '_set_%s' % item, None)
            if meth:
                meth(obj)
            elif obj.get(item) is not None:
                setattr(self, item, obj[item])

    def _set_enabled(self, obj):
        return obj['interfaceStatus'] != 'disabled'


class InterfaceFacts(ProviderBase):

    def generate(self):
        output = self.cli('show interfaces | json')
        facts = list()
        for item in itervalues(output['interfaces']):
            obj = Interface()
            obj.deserialize(item)
            facts.append(obj.serialize())
        return facts
