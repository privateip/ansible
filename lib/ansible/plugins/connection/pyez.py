# (c) 2016 Red Hat Inc.
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    author: Ansible Networking Team
    connection: network_cli
    short_description: Use network_cli to run command on network appliances
    description:
        - This plugin actually forces use of 'local' execution but using paramiko to establish a remote ssh shell on the appliance.
        - Also this plugin ignores the become_method but still uses the becoe_user and become_pass to
          do privilege escalation, method depending on network_os used.
    version_added: "2.3"
    options:
      network_os:
        description:
            - Appliance specific OS
        default: 'default'
        vars:
            - name: ansible_netconf_network_os
      password:
        description:
            - Secret used to authenticate
        vars:
            - name: ansible_pass
            - name: ansible_netconf_pass
      private_key_file:
        description:
            - Key or certificate file used for authentication
        ini:
            - section: defaults
              key: private_key_file
        env:
            - name: ANSIBLE_PRIVATE_KEY_FILE
        vars:
            - name: ansible_private_key_file
      timeout:
        type: int
        description:
          - Connection timeout in seconds
        default: 120
"""

import json
import logging
import re
import os
import signal
import socket
import traceback

from collections import Sequence

from ansible import constants as C
from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.six import BytesIO, binary_type
from ansible.module_utils._text import to_bytes, to_text
from ansible.plugins.loader import netconf_loader, connection_loader
from ansible.plugins.connection import ConnectionBase
from ansible.plugins.connection.local import Connection as LocalConnection
from ansible.utils.path import unfrackpath, makedirs_safe

try:
    from jnpr.junos import Device
except:
    raise AnsibleError("junos-eznc is not installed")

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class Connection(ConnectionBase):
    '''
    Juniper EZNC (NetConf) connection plugin
    '''
    transport = 'junos-eznc'
    has_pipelining = True
    force_persistence = True

    def __init__(self, play_context, new_stdin, *args, **kwargs):
        super(Connection, self).__init__(play_context, new_stdin, *args, **kwargs)

        self._manager = None
        self._netconf = None

        self._local = LocalConnection(play_context, new_stdin, *args, **kwargs)

        # reconstruct the socket_path and set instance values accordingly
        self._update_connection_state()

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            if name.startswith('_'):
                raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
            return getattr(self._netconf, name)

    def exec_command(self, cmd, in_data=None, sudoable=True):
        return self._local.exec_command(cmd, in_data, sudoable)

    def put_file(self, in_path, out_path):
        return self._local.put_file(in_path, out_path)

    def fetch_file(self, in_path, out_path):
        return self._local.fetch_file(in_path, out_path)

    def _connect(self):
        '''
        Connects to the remote device and starts the terminal
        '''
        if self.connected:
            return

        if self._play_context.password and not self._play_context.private_key_file:
            C.PARAMIKO_LOOK_FOR_KEYS = False

        self._manager = Device(
            host=self._play_context.remote_addr,
            port=self._play_context.port or 830,
            user=self._play_context.remote_user,
            password=self._play_context.password
        )

        self._manager.open()

        self._netconf = netconf_loader.get('junos', self)

        self._connected = True

        return self

    def _update_connection_state(self):
        '''
        Reconstruct the connection socket_path and check if it exists

        If the socket path exists then the connection is active and set
        both the _socket_path value to the path and the _connected value
        to True.  If the socket path doesn't exist, leave the socket path
        value to None and the _connected value to False
        '''
        ssh = connection_loader.get('ssh', class_only=True)
        cp = ssh._create_control_path(self._play_context.remote_addr, self._play_context.port, self._play_context.remote_user)

        tmp_path = unfrackpath(C.PERSISTENT_CONTROL_PATH_DIR)
        socket_path = unfrackpath(cp % dict(directory=tmp_path))

        if os.path.exists(socket_path):
            self._connected = True
            self._socket_path = socket_path

    def close(self):
        '''
        Close the active connection to the device
        '''
        # only close the connection if its connected.
        if self._connected:
            self._manager.close()
            self._connected = False
