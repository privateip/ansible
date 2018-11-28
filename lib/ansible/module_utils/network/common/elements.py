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
import json
import unicodedata

from collections import MutableMapping

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible.module_utils._text import to_text
from ansible.module_utils.six import with_metaclass
from ansible.module_utils.six import iteritems
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.common.config import NetworkConfig


class Attribute(object):

    def __init__(self, default=None, type=None, required=None, choices=None, cls=None, load_order=None):
        self.required = required
        self.attrtype = type
        self.value = None
        self.cls = cls
        self.default = default
        self.load_order = load_order

        if self.default is None:
            if self.cls is not None:
                if self.attrtype is None:
                    self.default = cls()
            elif self.attrtype == 'list':
                self.default = []
            elif self.attrtype == 'dict':
                self.default = {}

        assert isinstance(choices, list) or choices == None
        self.choices = choices

        if self.attrtype == 'int':
            self._attr_type = int
        elif self.attrtype == 'bool':
            self._attr_type = bool
        elif self.attrtype == 'list':
            self._attr_type = list
        elif self.attrtype == 'dict':
            self._attr_type = dict
        else:
            self._attr_type = str

    def __call__(self, value):
        if value is not None:
            if self.attrtype not in ('list', 'dict') and self.cls is None:

                if self.attrtype == 'bool' and not isinstance(value, bool):
                    raise ValueError('expected type bool')

                value = self._attr_type(value)

                if not isinstance(value, self._attr_type):
                    raise ValueError('invalid attribute type: %s' % value)

            if isinstance(value, unicode):
                value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')

            elif self.choices and value not in self.choices:
                raise ValueError('invalid value: %s' % value)

        return value


class BaseMeta(type):

    def __new__(cls, name, parents, dct):

        dct['_attributes'] = {}
        dct['_load_order'] = {}

        keys = list(dct.keys())

        for attr_name in keys:
            value = dct[attr_name]

            if isinstance(value, Attribute):
                if attr_name.startswith('_'):
                    attr_name = attr_name[1:]
                dct['_attributes'][attr_name] = value

                if value.load_order not in dct['_load_order']:
                    dct['_load_order'][value.load_order] = list()
                dct['_load_order'][value.load_order].append(attr_name)

        return super(ElementMeta, cls).__new__(cls, name, parents, dct)


class Base(with_metaclass(BaseMeta)):

    supported_connections = ('network_cli',)

    def __init__(self, **kwargs):
        self._command_output = {}
        self._connection = None

        required_attrs = list()

        for key, value in iteritems(self._attributes):
            try:
                attr_value = kwargs[key]
            except KeyError:
                attr_value = value.default
            setattr(self, key, attr_value)

            if value.required is True:
                required_attrs.append(key)

        for key in required_attrs:
            if getattr(self, key) is None:
                raise ValueError('missing required attribute: %s' % key)

        super(Base, self).__init__()

    def __setattr__(self, key, value):
        if key in self._attributes:
            value = self._attributes[key](value)
        print 'setting attribute %s to %s' % (key, value)
        self.__dict__[key] = value

    def __delattr__(self, key):
        attr = self._attributes.get(key)
        if attr.required is True:
            raise ValueError('required attributes cannot be deleted')
        elif attr.cls:
            self.__dict__[key] = attr.cls()
        else:
            self.__dict__[key] = attr.default

    def serialize(self):
        """Serialize the provider implementation into a JSON data structure
        """
        obj = {}
        for key, attr in iteritems(self._attributes):
            value = getattr(self, key)
            if attr.cls:
                obj[key] = value.serialize()
            else:
                obj[key] = value
        return obj

    def deserialize(self, ds):
        assert isinstance(ds, dict)
        for key, value in iteritems(ds):
            attr = self._attributes[key]
            if attr.cls:
                getattr(self, key).deserialize(value)
            else:
                setattr(self, key, value)


    def get_section(self, config, section, indent=1):
        if config is not None:
            netcfg = NetworkConfig(indent=indent, contents=config)
            try:
                config = netcfg.get_block_config(to_list(section))
            except ValueError:
                config = None
            return config

    def cli(self, command):
        try:
            return self._command_output[command]
        except KeyError:
            out = self._connection.get(command)
            try:
                out = json.loads(out)
            except ValueError:
                pass
            self._command_output[command] = out
            return out


class ConfigBase(Base):

    def __init__(self, *args, **kwargs):
        super(ConfigBase, self).__init__(*args, **kwargs)
        self._rendered_configuration = {}

    def render(self, config=None, operation=None):
        """Render the data structure into a set of CLI commands
        """
        raise NotImplementedError

    def parse(self, config=None):
        """Parse an existing configuration and return structured data
        """
        raise NotImplementedError

    def context_config(self, cmd):
        if 'context' not in self._rendered_configuration:
            self._rendered_configuration['context'] = list()
        self._rendered_configuration['context'].extend(to_list(cmd))

    def global_config(self, cmd):
        if 'global' not in self._rendered_configuration:
            self._rendered_configuration['global'] = list()
        self._rendered_configuration['global'].extend(to_list(cmd))

    def get_rendered_configuration(self):
        config = list()
        for section in ('context', 'global'):
            config.extend(self._rendered_configuration.get(section, []))
        return config

    def run(self, connection, check_mode=False):
        config = connection.get_config()

        commands = self.render(config)
        changed = bool(commands)

        if changed and not check_mode:
            connection.edit_config(commands)

        return {
            'changed': changed,
            'commands': commands
        }


class FactBase(Base):

    def populate(self):
        raise NotImplementedError


class ObjectCollection(MutableMapping):

    def __init__(self, *args, **kwargs):
        super(ObjectCollection, self).__init__(*args, **kwargs)
        self.items = {}

    def __getitem__(self, key):
        return self.__dict__['items'][key]

    def __setitem__(self, key, value):
        if not isinstance(value, self.__item_class__):
            raise TypeError('invalid type')
        self.__dict__['items'][key] = value

    def __delitem__(self, key):
        del self.__dict__['items'][key]

    def __iter__(self):
        return iter(self.__dict__['items'])

    def __len__(self):
        return len(self.__dict__['items'])

    def add(self, **kwargs):
        obj = self.__item_class__(**kwargs)
        key = getattr(obj, self.__item_id__)
        self[key] = obj
        return obj

    def get(self, key):
        return self[key]

    def get_all(self):
        objects = {}
        for key, value in iteritems(self.items):
            objects[key] = value.serialize()
        return objects

    def remove(self,key):
        del self[key]

    def deserialize(self, ds):
        assert isinstance(ds, dict)
        for key, value in iteritems(ds):
            value[self.__item_id__] = key
            self.add(**value)

    def serialize(self):
        obj = {}
        for key, value in iteritems(self.items):
            obj[key] = value.serialize()
        return obj

    def render(self, config=None, operation=None):
        raise NotImplementedError(self.__class__.__name__)
