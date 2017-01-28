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

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import patch, MagicMock
from ansible.errors import AnsibleModuleExit
from ansible.modules.network.eos import eos_acl
from ansible.module_utils import basic
from ansible.module_utils.local import LocalAnsibleModule
from ansible.module_utils._text import to_bytes


def set_module_args(args):
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)

fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures')
fixture_data = {}

def load_fixture(name):
    path = os.path.join(fixture_path, name)

    if path in fixture_data:
        return fixture_data[path]

    with open(path) as f:
        data = f.read()

    try:
        data = json.loads(data)
    except:
        pass

    fixture_data[path] = data
    return data


class TestEosAclModule(unittest.TestCase):

    def setUp(self):
        self.mock_load_config = patch('ansible.modules.network.eos.eos_acl.load_config')
        self.load_config = self.mock_load_config.start()

    def tearDown(self):
        self.mock_load_config.stop()

    def execute_module(self, failed=False, changed=False, commands=None,
            fixture=None, sort=True):

        self.load_config.return_value = dict(diff=None, session='session')

        with patch.object(LocalAnsibleModule, 'exec_command') as mock_exec_command:
            if fixture:
                out = load_fixture(fixture)
                mock_exec_command.return_value = (0, out, '')
            else:
                mock_exec_command.return_value = (1, '', 'error')

            with self.assertRaises(AnsibleModuleExit) as exc:
                eos_acl.main()

        result = exc.exception.result

        if failed:
            self.assertTrue(result['failed'], result)
        else:
            self.assertEqual(result.get('changed'), changed, result)

        if commands:
            if sort:
                self.assertEqual(sorted(commands), sorted(result['commands']), result['commands'])
            else:
                self.assertEqual(commands, result.get('commands'), result)

        return result

    def start_unconfigured(self, *args, **kwargs):
        return self.execute_module(*args, **kwargs)

    def start_configured(self, *args, **kwargs):
        kwargs['fixture'] = 'eos_acl_show_ip_access_list.txt'
        return self.execute_module(*args, **kwargs)

    def test_eos_acl_create(self):
        set_module_args(dict(name='example', seqno=10, action='permit', src='any'))
        commands = ['ip access-list standard example',
                    '10 permit any',
                    'exit']
        self.start_unconfigured(changed=True, commands=commands)

    def test_eos_acl_delete(self):
        set_module_args(dict(name='ansible', state='absent'))
        commands = ['no ip access-list standard ansible']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_delete_seqno(self):
        set_module_args(dict(name='ansible', seqno=10, state='absent'))
        commands = ['ip access-list standard ansible',
                    'no 10', 'exit']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_replace_seqno(self):
        set_module_args(dict(name='ansible', seqno=10, action='deny', src='any'))
        commands = ['ip access-list standard ansible',
                    'no 10', '10 deny any', 'exit']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_add_seqno_dotted(self):
        src = '192.168.1.1 255.255.255.0'
        set_module_args(dict(name='ansible', seqno=100, action='deny', src=src))
        commands = ['ip access-list standard ansible',
                    '100 deny 192.168.1.0 255.255.255.0',
                    'exit']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_add_seqno(self):
        src = '192.168.1.1/24'
        set_module_args(dict(name='ansible', seqno=100, action='deny', src=src))
        commands = ['ip access-list standard ansible',
                    '100 deny 192.168.1.0/24',
                    'exit']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_entries(self):
        entries = [{'seqno': 100, 'src': 'any'}]
        set_module_args(dict(name='ansible', entries=entries))
        commands = ['ip access-list standard ansible',
                    '100 permit any', 'exit']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_entries_missing_src(self):
        entries = [{'seqno': 100}]
        set_module_args(dict(name='ansible', entries=entries))
        self.start_configured(failed=True)

    def test_eos_acl_log(self):
        set_module_args(dict(name='ansible', seqno=100, src='any', log=True))
        commands = ['ip access-list standard ansible',
                    '100 permit any log', 'exit']
        self.start_configured(changed=True, commands=commands)

    def test_eos_acl_nochange(self):
        set_module_args(dict(name='ansible', seqno=10, src='any'))
        self.start_configured()

    def test_eos_acl_purge(self):
        set_module_args(dict(name='ansible', seqno=10, purge=True, state='absent'))
        commands = ['ip access-list standard ansible', 'no 10', 'no 20', 'no 30',
                    'no 40', 'no 50', 'no 60', 'no 70', 'exit']
        self.start_configured(changed=True, commands=commands)



