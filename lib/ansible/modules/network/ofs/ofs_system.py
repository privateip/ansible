#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
#
# This file is part of Ansible by Red Hat
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'core'}


DOCUMENTATION = """
"""

EXAMPLES = """
"""

RETURN = """
"""
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible.module_utils.network_common import dict_diff


CONFIG_KEYS = frozenset([
    ('hostname', 'Hostname'),
    ('description', 'Description')
])


STATE_KEYS = frozenset([
])

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


def set_object(module, item):
    url = 'http://%s:%s/public/v1/config/SystemParam' % (module.params['api_host'], module.params['api_port'])

    result = {'changed': True}

    obj = {}
    for param, key in CONFIG_KEYS:
        if item.get(param) is not None:
            func = globals().get('set_%s' % param)
            if func:
                value = func(item)
            else:
                value = item[param]
            obj[key] = value

    if not module.check_mode:
        update_object(module, url, obj)

    return result

def get_desired_config(module):
    params = [item[0] for item in CONFIG_KEYS]
    return dict([(key,  module.params[key]) for key in params])


def get_desired_state(module):
    params = [item[0] for item in STATE_KEYS]
    return dict([(key,  module.params[key]) for key in params])


def get_current(module, keys, data):
    obj = {}
    for param, key in keys:
        func = globals().get('get_%s' % param)
        if func:
            value = func(data)
        else:
            value = data['Object'][key]
        obj[param] = value
    return obj


def get_current_config(module):
    url = 'http://%s:%s/public/v1/config/SystemParam' % (module.params['api_host'], module.params['api_port'])
    output = get_object(module, url)
    return get_current(module, CONFIG_KEYS, output)


def get_current_state(module):
    url = 'http://%s:%s/public/v1/state/SystemParam' % (module.params['api_host'], module.params['api_port'])
    output = get_object(module, url)
    return get_current(module, STATE_KEYS, output)

def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        hostname=dict(),
        description=dict(),

        api_host=dict(default='localhost'),
        api_port=dict(type='int', default=8080),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    desired_config = get_desired_config(module)
    current_config = get_current_config(module)

    result = {'changed': False}

    if dict_diff(current_config, desired_config):
        result['changed'] = True
        if not module.check_mode:
            set_object(module, desired_config)

    if result['changed']:
        time.sleep(module.params['delay'])

    current_state = get_current_state(module)
    desired_state = get_desired_state(module)

    for key, _ in STATE_KEYS:
        if desired_state[key] is not None:
            try:
                if not test(desired_state[key], current_state[key]):
                    module.fail_json(
                        msg='BGP failed `%s` check, wanted %s, got %s' % \
                            (key, desired_state[key], current_state[key])
                    )
            except Exception as exc:
                module.fail_json(msg=str(exc))


    module.exit_json(**result)

if __name__ == '__main__':
    main()
