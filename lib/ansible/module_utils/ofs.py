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
import time

from collections import Mapping, namedtuple

from ansible.module_utils.six import itervalues, iteritems
from ansible.module_utils.urls import fetch_url
from ansible.module_utils.network_common import dict_diff, test_value


def send_request(module, url, method, data=None):
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    return fetch_url(module, url, data=data, headers=headers, method=method)


def get_object(module, url, obj=None):
    data = module.jsonify(obj) if obj else None
    resp, info = send_request(module, url, method='GET', data=data)
    if info['status'] != 200:
        # TODO write a better failure message
        module.fail_json(**info)
    return module.from_json(resp.read())


def insert_object(module, url, obj):
    data = module.jsonify(obj)
    resp, info = send_request(module, url, method='POST', data=data)
    if info['status'] != 201:
        # TODO write a better failure message
        module.fail_json(**info)


def delete_object(module, url, obj):
    data = module.jsonify(obj)
    resp, info = send_request(module, url, method='DELETE', data=data)
    if info['status'] != 410:
        # TODO write a better failure message
        module.fail_json(**info)


def update_object(module, url, obj):
    data = module.jsonify(obj)
    resp, info = send_request(module, url, method='PATCH', data=data)
    if info['status'] != 200:
        body = module.from_json(info['body'])
        result = body['Result']
        module.fail_json(msg=info['msg'], status=info['status'], result=result)


def match_object(item, iterable, ref):
    for obj in iterable:
        if item[ref] == obj[ref]:
            return obj

def make_url(module, path):
    url_base = 'http://%s:%s/public/v1' % (module.params['api_host'], module.params['api_port'])
    if path[0] == '/':
        path = path[1:]
    return '%s/%s' % (url_base, path)


MappedKey = namedtuple('MappedKey', 'param, key, getter, setter, transform, check')


def mapped_key(param, key=None, getter=None, setter=None, transform=None, check=None):
    return MappedKey(param, key, getter, setter, transform, check)


class BaseObject(object):

    def __init__(self, module, keymap, getter_url, ref=None, static_map=None):
        self.module = module
        self.keymap = dict([(i.param, i) for i in keymap])

        self.ref = ref
        self.getter_url = getter_url
        self.static_map = static_map

        if self.ref and self.ref not in self.keymap:
            module.fail_json(msg='ref not found in keymap')

    def load_from_device(self):
        defaults = self.static_map or {}

        response = get_object(self.module, self.getter_url)
        objects = list()

        if 'Objects' in response:
            data = response['Objects']
        else:
            data = [response]

        for entry in data:
            obj = {}
            for item in itervalues(self.keymap):
                try:
                    value = entry['Object'][item.key]
                except KeyError:
                    value = defaults.get(item.param)

                if item.getter:
                    value = item.getter(value)

                obj[item.param] = value
            objects.append(obj)

        return objects

    def _load_params(self, data, defaults=None):
        obj = {}

        for item in itervalues(self.keymap):
            try:
                value = data[item.param]
            except KeyError:
                value = None

            if not value and defaults:
                value = defaults[item.param]

            if value:
                if item.transform:
                    value = item.transform(value)

            obj[item.param] = value
        return obj

    def load_from_params(self):
        objects = list()

        if 'aggregate' in self.module.params and self.module.params['aggregate'] is not None:
            for item in self.module.params['aggregate']:
                if isinstance(item, Mapping):
                    objects.append(self._load_params(item, self.module.params))
                else:
                    objects.append(self._load_params({self.ref: item}, self.module.params))
        elif 'purge' in self.module.argument_spec and self.module.params['purge'] != True:
            if self.ref and self.module.params[self.ref] is None:
                self.module.fail_json(msg='missing required argument: %s' % self.ref)
            objects.append(self._load_params(self.module.params))
        else:
            objects.append(self._load_params(self.module.params))

        return objects


class ConfigObject(BaseObject):

    def __init__(self, module, keymap, getter_url, setter_url, ref=None, static_map=None):
       super(ConfigObject, self).__init__(module, keymap, getter_url, ref, static_map)
       self.setter_url = setter_url
       self.purge = True

    def send_to_device(self, objects):
        for method, item in objects:
            obj = {}

            for entry in itervalues(self.keymap):
                if item.get(entry.param) is not None:
                    value = item[entry.param]

                    if entry.setter:
                        value = entry.setter(value)

                    if entry.key is not None:
                        obj[entry.key] = value

            url = self.setter_url or self.getter_url
            func = globals().get('%s_object' % method)
            func(self.module, url, obj)

    def run(self):
        result = {'changed': False}
        updates = list()

        desired_config = self.load_from_params()
        current_config = self.load_from_device()

        # XXX tracking a state argument here
        if 'state' in self.keymap:
            result.update({'added': [], 'deleted': [], 'updated': [], 'purged': []})

        import q
        q(desired_config)
        q(current_config)

        for desired_item in desired_config:
            if self.ref:
                current_item = match_object(desired_item, current_config, self.ref)
            else:
                current_item = current_config[0]

            # XXX tracking a state argument here
            if 'state' in desired_item:
                if not current_item and desired_item['state'] != 'absent':
                    updates.append(('insert', desired_item))
                    result['added'].append(desired_item[self.ref])

                elif current_item and desired_item['state'] == 'absent':
                    updates.append(('delete', desired_item))
                    result['deleted'].append(desired_item[self.ref])

                elif current_item:
                    diff = dict_diff(current_item, desired_item)
                    if diff and diff.keys() != ['state']:
                        updates.append(('update', desired_item))
                        result['updated'].append(desired_item[self.ref])

            else:
                diff = dict_diff(current_item, desired_item)
                q(diff)
                if diff:
                    updates.append(('update', desired_item))

        if 'purge' in self.module.params and self.module.params['purge']:
            for current_item in current_config:
                if not match_object(current_item, desired_config, self.ref):
                    updates.append(('delete', current_item))
                    result['purged'].append(current_item[self.ref])

        q(updates)

        if updates:
            result['changed'] = True
            if not self.module.check_mode:
                self.send_to_device(updates)

        return result


class StateObject(BaseObject):

    def run(self, changed=True):
        assert self.getter_url is not None

        desired_state = self.load_from_params()
        current_state = self.load_from_device()

        delay = self.module.params['delay']
        result = {}
        facts = {}

        for desired_item in desired_state:
            if self.ref:
                current_item = match_object(desired_item, current_state, self.ref)

                # XXX tracking a state argument here
                if desired_item.get('state', 'present') == 'absent':
                    continue

            else:
                current_item = current_state[0]

            if not current_item:
                self.module.fail_json(msg='unable to match object %s' % desired_item[self.ref])

            for key, value in iteritems(self.keymap):
                if current_item[key] is not None:
                    if self.ref:
                        ref_value = current_item[self.ref]
                        if ref_value not in facts:
                            facts[ref_value] = {}
                        if key != self.ref:
                            facts[ref_value][key] = current_item[key]
                    else:
                        facts[key] = current_item[key]

                if desired_item[key] is not None:
                    if changed and delay:
                        time.sleep(delay)
                        delay = 0

                    if self.ref:
                        msg = 'conditional check failed for argument: %s for %s %s, wanted: %s got: %s' % \
                              (key, self.ref, desired_item[self.ref], desired_item[key], current_item[key])
                    else:
                        msg = 'conditional check failed for argument: %s, wanted: %s, got: %s' %  \
                            (key, desired_item[key], current_item[key])

                    try:
                        if value.check:
                            if value.check(desired_item[key], current_item[key]) is False:
                                self.module.fail_json(msg=msg)
                        else:
                            if not test_value(desired_item[key], current_item[key]):
                                self.module.fail_json(msg=msg)
                    except Exception as exc:
                        self.module.fail_json(msg=str(exc))

        result.update({'state': facts})
        return result

class Runner:

    def __init__(self, module):
        self.module = module
        self._config_kwargs = {'module': module}
        self._state_kwargs = {'module': module}

    def set_config_keymap(self, obj):
        self._config_kwargs['keymap'] = obj

    def set_state_keymap(self, obj):
        self._state_kwargs['keymap'] = obj

    def set_getter_url(self, url):
        self._config_kwargs['getter_url'] = url

    def set_setter_url(self, url):
        self._config_kwargs['setter_url'] = url

    def set_state_url(self, url):
        self._state_kwargs['getter_url'] = url

    def set_static_map(self, obj):
        self._config_kwargs['static_map'] = obj

    def set_reference_key(self, key):
        self._config_kwargs['ref'] = key
        self._state_kwargs['ref'] = key

    def run(self):
        try:
            config_object = ConfigObject(**self._config_kwargs)
            result = config_object.run()

            if 'keymap' in self._state_kwargs:
                state_object = StateObject(**self._state_kwargs)
                result.update(state_object.run(result['changed']))

            return result

        except Exception as exc:
            self.module.fail_json(msg=str(exc))
