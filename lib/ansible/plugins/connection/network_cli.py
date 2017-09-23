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
from ansible.plugins.loader import cliconf_loader, terminal_loader, connection_loader
from ansible.plugins.connection.jsonrpc import Connection as BaseConnection
from ansible.plugins.connection.paramiko_ssh import Connection as Ssh
from ansible.utils.path import unfrackpath, makedirs_safe

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class Connection(BaseConnection):
    ''' CLI (shell) SSH connections on Paramiko '''

    transport = 'network_cli'
    has_pipelining = True
    startable = True

    def __init__(self, play_context, new_stdin, *args, **kwargs):
        super(Connection, self).__init__(play_context, new_stdin, *args, **kwargs)

        self.ssh = None

        self._terminal = None
        self._cliconf = None
        self._ssh_shell = None
        self._matched_prompt = None
        self._matched_pattern = None
        self._last_response = None
        self._history = list()

        self._play_context = play_context

        if play_context.verbosity > 3:
            logging.getLogger('paramiko').setLevel(logging.DEBUG)

    def update_play_context(self, play_context):
        """Updates the play context information for the connection"""

        display.vvvv('updating play_context for connection', host=self._play_context.remote_addr)

        if self._play_context.become is False and play_context.become is True:
            auth_pass = play_context.become_pass
            self._terminal.on_authorize(passwd=auth_pass)

        elif self._play_context.become is True and not play_context.become:
            self._terminal.on_deauthorize()

        self._play_context = play_context

    def start_connection(self, play_context):
        """Connections to the device and sets the terminal type"""

        if self._play_context.password and not self._play_context.private_key_file:
            C.PARAMIKO_LOOK_FOR_KEYS = False

        # assign the remote user to the connection user to make sure the
        # correct username is passed to paramiko
        play_context.remote_user = play_context.connection_user

        ssh = Ssh(play_context, '/dev/null')._connect()
        self.ssh = ssh.ssh

        display.vvvv('ssh connection done, setting terminal', host=self._play_context.remote_addr)

        self._ssh_shell = self.ssh.invoke_shell()
        self._ssh_shell.settimeout(self._play_context.timeout)

        network_os = self._play_context.network_os
        if not network_os:
            raise AnsibleConnectionFailure(
                'Unable to automatically determine host network os. Please '
                'manually configure ansible_network_os value for this host'
            )

        self._terminal = terminal_loader.get(network_os, self)
        if not self._terminal:
            raise AnsibleConnectionFailure('network os %s is not supported' % network_os)

        display.vvvv('loaded terminal plugin for network_os %s' % network_os, host=self._play_context.remote_addr)

        self._cliconf = cliconf_loader.get(network_os, self)
        if self._cliconf:
            self.register_object(self._cliconf)
            self.register_object(self.reset)
            display.vvvv('loaded cliconf plugin for network_os %s' % network_os, host=self._play_context.remote_addr)
        else:
            display.vvvv('unable to load cliconf for network_os %s' % network_os)

        self.receive()

        display.vvvv('firing event: on_open_shell()', host=self._play_context.remote_addr)
        self._terminal.on_open_shell()

        if getattr(self._play_context, 'become', None):
            display.vvvv('firing event: on_authorize', host=self._play_context.remote_addr)
            auth_pass = self._play_context.become_pass
            self._terminal.on_authorize(passwd=auth_pass)

        display.vvvv('ssh connection has completed successfully', host=self._play_context.remote_addr)

    def reset(self):
        """ Reset the connection
        """
        ssh = connection_loader.get('ssh', class_only=True)
        cp = ssh._create_control_path(self._play_context.remote_addr, self._play_context.port, self._play_context.remote_user)

        tmp_path = unfrackpath(C.PERSISTENT_CONTROL_PATH_DIR)
        socket_path = unfrackpath(cp % dict(directory=tmp_path))

        display.vvv('socket_path %s' % socket_path, host=self._play_context.remote_addr)

        if os.path.exists(socket_path):
            setattr(self, 'socket_path', socket_path)
            display.vvvv('shutting down socket due to reset_connection', host=self._play_context.remote_addr)
            self.shutdown()
        else:
            display.vvvv('socket_path does not exist', host=self._play_context.remote_addr)

    def close(self):
        """Close the active connection to the device
        """
        display.vvvv("closing ssh connection to device", host=self._play_context.remote_addr)
        if self._ssh_shell:
            display.vvvv("firing event: on_close_shell()", host=self._play_context.remote_addr)
            self._terminal.on_close_shell()
            self._ssh_shell.close()
            self._ssh_shell = None
            display.vvvv("cli session is now closed", host=self._play_context.remote_addr)

        super(Connection, self).close()

        self._connected = False
        display.vvvv("ssh connection has been closed successfully", host=self._play_context.remote_addr)

    def receive(self, command=None, prompts=None, answer=None):
        """Handles receiving of output from command"""
        recv = BytesIO()
        handled = False

        self._matched_prompt = None

        while True:
            data = self._ssh_shell.recv(256)

            recv.write(data)
            offset = recv.tell() - 256 if recv.tell() > 256 else 0
            recv.seek(offset)

            window = self._strip(recv.read())

            if prompts and not handled:
                handled = self._handle_prompt(window, prompts, answer)

            if self._find_prompt(window):
                self._last_response = recv.getvalue()
                resp = self._strip(self._last_response)
                return self._sanitize(resp, command)

    def send(self, command, prompts=None, answer=None, send_only=False):
        """Sends the command to the device in the opened shell"""
        try:
            self._history.append(command)
            self._ssh_shell.sendall(b'%s\r' % command)
            if send_only:
                return
            return self.receive(command, prompts, answer)
        except (socket.timeout, AttributeError):
            display.vvvv(traceback.format_exc(), host=self._play_context.remote_addr)
            raise AnsibleConnectionFailure("timeout trying to send command: %s" % command.strip())

    def _strip(self, data):
        """Removes ANSI codes from device response"""
        for regex in self._terminal.ansi_re:
            data = regex.sub(b'', data)
        return data

    def _handle_prompt(self, resp, prompts, answer):
        """
        Matches the command prompt and responds

        :arg resp: Byte string containing the raw response from the remote
        :arg prompts: Sequence of byte strings that we consider prompts for input
        :arg answer: Byte string to send back to the remote if we find a prompt.
                A carriage return is automatically appended to this string.
        :returns: True if a prompt was found in ``resp``.  False otherwise
        """
        prompts = [re.compile(r, re.I) for r in prompts]
        for regex in prompts:
            match = regex.search(resp)
            if match:
                self._ssh_shell.sendall(b'%s\r' % answer)
                return True
        return False

    def _sanitize(self, resp, command=None):
        """Removes elements from the response before returning to the caller"""
        cleaned = []
        for line in resp.splitlines():
            if (command and line.strip() == command.strip()) or self._matched_prompt.strip() in line:
                continue
            cleaned.append(line)
        return b'\n'.join(cleaned).strip()

    def _find_prompt(self, response):
        """Searches the buffered response for a matching command prompt"""
        errored_response = None
        is_error_message = False
        for regex in self._terminal.terminal_stderr_re:
            if regex.search(response):
                is_error_message = True

                # Check if error response ends with command prompt if not
                # receive it buffered prompt
                for regex in self._terminal.terminal_stdout_re:
                    match = regex.search(response)
                    if match:
                        errored_response = response
                        break

        if not is_error_message:
            for regex in self._terminal.terminal_stdout_re:
                match = regex.search(response)
                if match:
                    self._matched_pattern = regex.pattern
                    self._matched_prompt = match.group()
                    if not errored_response:
                        return True

        if errored_response:
            raise AnsibleConnectionFailure(errored_response)

        return False

    def alarm_handler(self, signum, frame):
        """Alarm handler raised in case of command timeout """
        display.vvvv('closing shell due to sigalarm', host=self._play_context.remote_addr)
        self.close()

