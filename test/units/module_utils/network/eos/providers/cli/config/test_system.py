# -*- coding: utf-8 -*-
#
# (c) 2017 Red Hat, Inc.
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
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible.module_utils.network.eos.providers.cli.config.system import Provider


def test_render():
    params = {
        'hostname': 'localhost',
        'domain_name': 'redhat.com',
        'domain_search': ['ansible.com', 'redhat.com'],
        'lookup_source': 'Ma1',
        'name_servers': ['8.8.8.8', '8.8.4.4']
    }

    p = Provider(params=params)
    commands = p.render()

    assert len(commands) == 7
    assert 'hostname localhost' in commands
    assert 'ip domain-name redhat.com' in commands
    assert 'ip domain-list ansible.com' in commands
    assert 'ip domain-list redhat.com' in commands
    assert 'ip domain lookup source-interface Ma1' in commands
    assert 'ip name-server vrf default 8.8.8.8' in commands
    assert 'ip name-server vrf default 8.8.4.4' in commands
