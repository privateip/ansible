#!/usr/bin/python
#
# This file is part of Ansible
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

ANSIBLE_METADATA = {
    'status': ['preview'],
    'supported_by': 'core',
    'version': '1.0'
}

DOCUMENTATION = """
---
module: eos_acl_
version_added: "2.3"
author: "Peter Sprygada (@privateip)"
short_description: Manages standard ACLs on Arista EOS devices
description:
  - This module provides management of access-list entries on remote
    device running Arista EOS.  It allows for the creation and deletion
    of specific ACL entries as well as removing entire access-lists from
    the running config.
options:
  name:
    description:
      - The C(name) argument specifies the name of the access-list
        to configure.  The access-list name must be unique in the
        device running configuration.  If a previously configured
        access-list of a different type (std, ext) is found, this will
        cause an module failure.
    required: true
    default: null
  seqno:
    description:
      - The C(seqno) argument specifies the individual access-list entry
        to apply the configuration towards.  The C(seqno) argument is
        required if the state is C(present).  This argument accepts
        integer values in the range of 1 to 4294967295.
    required: false
    default: null
  action:
    description:
      - The C(action) argument configures the type of access-list entry
        to construct as either a permit entry or a deny entry.  This
        argument only accepts values of C(permit) or C(deny)
    required: false
    choices: ['permit', 'deny']
    default: permit
  src:
    description:
      - The C(src) arugment classifies the source IP information to
        identify interesting traffic.  This argument accepts any of the
        following formats - C(any), C(host A.B.C.D), C(A.B.C.D/E) or
        C(A.B.C.D E.F.G.H)
    required: false
    default: null
  log:
    description:
      - The C(log) argument will configure the access-list entry to log
        all traffic that matches this access-list entry.  This boolean
        value with either append or remove the C(log) command line
        argument
    required: false
    choices: ['true', 'false']
    default: null
  state:
    description:
      - The C(state) argument configures the state of the configuration
        values in the device's current active configuration.  When set
        to I(present), the values should be configured in the device active
        configuration and when set to I(absent) the values should not be
        in the device active configuration
    required: false
    default: present
    choices: ['present', 'absent']
"""

EXAMPLES = """
- name: configure an access-list entry
  eos_acl:
    name: playbook
    seqno: 10
    action: permit
    src: any
    log: yes

- name: remove a specific acl entry
  eos_acl:
    name: playbook
    seqno: 40
    state: absent

- name: remove the whole acl
  eos_acl:
    name: playbook
    state: absent
"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: always
  type: list
  sample:
    - ip access-list standard ansible
    - 10 permit host 1.2.3.4
    - 20 deny any log
session_name:
  description: The EOS config session name used to load the configuration
  returned: when changed is True
  type: str
  sample: ansible_1479315771
start:
  description: The time the job started
  returned: always
  type: str
  sample: "2016-11-16 10:38:15.126146"
end:
  description: The time the job ended
  returned: always
  type: str
  sample: "2016-11-16 10:38:25.595612"
delta:
  description: The time elapsed to perform all operations
  returned: always
  type: str
  sample: "0:00:10.469466"
"""
import re
from functools import partial

from ansible.module_utils.local import LocalAnsibleModule
from ansible.module_utils.eos import load_config, run_commands
from ansible.module_utils.six import iteritems
from ansible.module_utils.network_common import to_subnet

def needs_update(want, have):
    for key, value in iteritems(want):
        if value and value != have.get(key):
            return True

def map_obj_to_commands(updates, module):
    commands = list()

    for update in updates:
        want, have = update

        if needs_update(want, have):
            if want['state'] == 'absent' and have['state'] == 'present':
                commands.append('no %s' % want['seqno'])

            elif want['state'] == 'present':
                cmd = list()
                for key in ('seqno', 'action', 'src'):
                    if want[key]:
                        cmd.append(str(want[key]))

                if want['log']:
                    cmd.append('log')

                if have.get('state') == 'present':
                    commands.append('no %s' % want['seqno'])

                commands.append(' '.join(cmd))

    return commands

def map_config_to_obj(module):
    cmd = 'show ip access-list %s' % module.params['name']
    rc, out, err = module.exec_command(cmd)

    instance = {'name': module.params['name'], 'entries': list(),
                'state': module.params['state']}

    if rc == 0:
        if not out.startswith('Standard'):
            module.fail_json(msg='access-list name already in use')

        instance['state'] = 'present'

        regex = r'^\s+(?:(\d+) (\w+) (.+?)(?: (log))*$)'
        for match in re.finditer(regex, out, re.S|re.M):
            instance['entries'].append({
                'name': module.params['name'],
                'seqno': int(match.group(1)),
                'action': match.group(2),
                'src': match.group(3),
                'log': match.group(4) is not None,
                'state': 'present'
            })

    return instance

def validate_seqno(value, module):
    if not 1 <= value <= 4294967295:
        module.fail_json(msg='seqno must be between 1 and 4294967295')

def normalize_src(value):
    if not value:
        return

    for kw in ['host', 'any']:
        if kw in value:
            return value

    if '/' in value:
        src_net, src_mask = value.split('/')
        dotted_notation = False
    elif ' ' in value:
        src_net, src_mask = value.split(' ')
        dotted_notation = True
    else:
        module.fail_json(msg='unable to parse src value')

    subnet = to_subnet(src_net, src_mask, dotted_notation)

    if dotted_notation:
        net, mask = subnet.split(' ')
    else:
        net, mask = subnet.split('/')

    if mask == '32' or mask == '255.255.255.255':
        return 'host %s' % masklen

    return subnet

def get_param_value(key, item, module):
    # if key doesn't exist in the item, get it from module.params
    if not item.get(key):
        value = module.params[key]

    # if key does exist, do a type check on it to validate it
    else:
        value_type = module.argument_spec[key].get('type', 'str')
        type_checker = module._CHECK_ARGUMENT_TYPES_DISPATCHER[value_type]
        type_checker(item[key])
        value = item[key]

    return value

def map_params_to_obj(module):
    entries = module.params['entries'] or list()

    if not entries and module.params['seqno']:
        entries.append({'seqno': module.params['seqno']})

    objects = list()

    for item in entries:
        if not isinstance(item, dict):
            module.fail_json(msg='argument entries must be of type dict')
        elif 'seqno' not in item:
            module.fail_json(msg='missing required argument: seqno')

        get_value = partial(get_param_value, item=item, module=module)

        item.update({
            'seqno': get_value('seqno'),
            'src': normalize_src(get_value('src')),
            'action': get_value('action'),
            'log': get_value('log'),
            'state': get_value('state')
        })

        if item['state'] == 'present' and not item['src']:
            module.fail_json(msg='missing required argument: src')

        for key, value in iteritems(item):
            # validate the param value (if validator func exists)
            if value:
                validator = globals().get('validate_%s' % key)
                if all((value, validator)):
                    validator(value, module)

        objects.append(item)

    return {'name': module.params['name'], 'entries': objects,
            'state': module.params['state']}

def update_objects(want, have):
    updates = list()
    for entry in want:
        item = next((i for i in have if i['seqno'] == entry['seqno']), None)
        if all((item is None, entry['state'] == 'present')):
            updates.append((entry, {}))
        elif item:
            for key, value in iteritems(entry):
                if value and value != item[key]:
                    updates.append((entry, item))
    return updates

def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        name=dict(required=True),

        entries=dict(type='list'),
        seqno=dict(type='int'),

        action=dict(choices=['permit', 'deny'], default='permit'),
        src=dict(),

        log=dict(type='bool'),

        purge=dict(type='bool'),
        state=dict(default='present', choices=['present', 'absent'])
    )

    mutually_exclusive = [('seqno', 'entries')]

    module = LocalAnsibleModule(argument_spec=argument_spec,
                                mutually_exclusive=mutually_exclusive,
                                supports_check_mode=True)

    result = {'changed': False}

    want = map_params_to_obj(module)
    have = map_config_to_obj(module)

    commands = list()

    if want['entries']:
        updates = update_objects(want['entries'], have['entries'])
        commands.extend(map_obj_to_commands(updates, module))

        if module.params['purge']:
            want_entries = [x['seqno'] for x in want['entries']]
            have_entries = [x['seqno'] for x in have['entries']]
            for item in set(have_entries).difference(want_entries):
                commands.append('no %s' % item)

        if commands:
            commands.insert(0, 'ip access-list standard %s' % module.params['name'])
            commands.append('exit')

    elif want['state'] == 'absent' and have['state'] == 'present':
        commands.append('no ip access-list standard %s' % module.params['name'])

    elif want['state'] == 'present' and have['state'] == 'absent':
        commands.append('ip access-list standard %s' % module.params['name'])

    result['commands'] = commands

    if commands:
        commit = not module.check_mode
        response = load_config(module, commands, commit=commit)
        if response.get('diff') and module._diff:
            result['diff'] = {'prepared': response.get('diff')}
        result['session_name'] = response.get('session')
        result['changed'] = True

    module.exit_json(**result)

if __name__ == '__main__':
    main()
