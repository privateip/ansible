#!/usr/bin/env python
#
# (c) 2016 Red Hat Inc.
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

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json

import ansible.module_utils.basic

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import patch, MagicMock
from ansible.errors import AnsibleModuleExit
from ansible.modules.network.eos import eos_ethernet


def set_module_args(args):
    json_args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    ansible.module_utils.basic._ANSIBLE_ARGS = json_args

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


class TestEosVlanModule(unittest.TestCase):

    def setUp(self):
        self.mock_run_commands = patch('ansible.modules.network.eos.eos_ethernet.run_commands')
        self.run_commands = self.mock_run_commands.start()

        self.mock_load_config = patch('ansible.modules.network.eos.eos_ethernet.load_config')
        self.load_config = self.mock_load_config.start()

    def tearDown(self):
        self.mock_run_commands.stop()
        self.mock_load_config.stop()

    def execute_module(self, failed=False, changed=False):

        self.load_config.return_value = dict(diff=None, session='session')

        with self.assertRaises(AnsibleModuleExit) as exc:
            eos_ethernet.main()

        result = exc.exception.result

        self.assertEqual(result['failed'], failed, result)
        if not failed:
            self.assertEqual(result['changed'], changed, result)

        return result

    def test_eos_ethernet_invalid_name(self):
        set_module_args(dict(name='foo'))
        self.execute_module(failed=True)

    def test_eos_ethernet_state(self):
        self.run_commands.return_value = [load_fixture('eos_ethernet_show_interfaces.json')]

        set_module_args(dict(name='Ethernet1', state='enabled'))
        result = self.execute_module(changed=False)
        self.assertEqual(result['commands'], [])

        set_module_args(dict(name='Ethernet1', state='disabled'))
        result = self.execute_module(changed=True)
        self.assertEqual(sorted(['interface Ethernet1', 'shutdown']), sorted(result['commands']))

    def test_eos_ethernet_description(self):
        self.run_commands.return_value = [load_fixture('eos_ethernet_show_interfaces.json')]

        set_module_args(dict(name='Ethernet1', description='test string'))
        result = self.execute_module(changed=True)
        self.assertEqual(sorted(['interface Ethernet1', 'description test string']), sorted(result['commands']))

    def test_eos_ethernet_oper_state(self):
        self.run_commands.return_value = [load_fixture('eos_ethernet_show_interfaces.json')]

        set_module_args(dict(name='Ethernet1', oper_status='down', delay=0))
        result = self.execute_module(failed=True)

        set_module_args(dict(name='Ethernet1', oper_status='up', delay=0))
        result = self.execute_module()

    def test_eos_ethernet_neighbors_host_only_pass(self):
        fixtures = ['eos_ethernet_show_interfaces.json', 'eos_ethernet_show_lldp_neighbors.json']

        def run_commands(*args):
            return [load_fixture(fixtures.pop(0))]
        self.run_commands.side_effect = run_commands

        set_module_args(dict(name='Ethernet1', neighbors=['veos03.eng.ansible.com']))
        result = self.execute_module()

    def test_eos_ethernet_neighbors_host_only_fail(self):
        fixtures = ['eos_ethernet_show_interfaces.json', 'eos_ethernet_show_lldp_neighbors.json']

        def run_commands(*args):
            return [load_fixture(fixtures.pop(0))]
        self.run_commands.side_effect = run_commands

        set_module_args(dict(name='Ethernet1', neighbors=['veos03']))
        result = self.execute_module(failed=True)

    def test_eos_ethernet_neighbors_host_and_port_pass(self):
        fixtures = ['eos_ethernet_show_interfaces.json', 'eos_ethernet_show_lldp_neighbors.json']

        def run_commands(*args):
            return [load_fixture(fixtures.pop(0))]
        self.run_commands.side_effect = run_commands

        set_module_args(dict(name='Ethernet1', neighbors=[{'host': 'veos03.eng.ansible.com', 'port': 'Ethernet1'}]))
        result = self.execute_module()

    def test_eos_ethernet_neighbors_host_and_port_fail(self):
        fixtures = ['eos_ethernet_show_interfaces.json', 'eos_ethernet_show_lldp_neighbors.json']

        def run_commands(*args):
            return [load_fixture(fixtures.pop(0))]
        self.run_commands.side_effect = run_commands

        set_module_args(dict(name='Ethernet1', neighbors=[{'host': 'veos03.eng.ansible.com', 'port': 'Ethernet2'}]))
        result = self.execute_module(failed=True)






