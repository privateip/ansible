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
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import logging
import re
import signal
import socket
import traceback
import uuid

from collections import Sequence

from ansible import constants as C
from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.six import BytesIO, binary_type, text_type
from ansible.module_utils._text import to_bytes, to_text
from ansible.plugins import cliconf_loader
from ansible.plugins.connection import ensure_connect
from ansible.plugins.connection.rpc import Rpc
from ansible.plugins.connection.paramiko_ssh import Connection as _Connection
from ansible.errors import AnsibleError, AnsibleConnectionFailure

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class Connection(Rpc, _Connection):
    """CLI (shell) SSH connections on Paramiko """

    transport = 'network_cli'
    has_pipelining = True

    def __init__(self, play_context, new_stdin, *args, **kwargs):
        super(Connection, self).__init__(play_context, new_stdin, *args, **kwargs)

        self._cliconf = None
        self._shell = None
        self._connected = False
        self._matched_prompt = None
        self._matched_pattern = None
        self._last_response = None
        self._history = list()

        if play_context.verbosity > 3:
            logging.getLogger('paramiko').setLevel(logging.DEBUG)

    def update_play_context(self, play_context):
        """Updates the play context information for the connection"""

        display.display('updating play_context for connection', log_only=True)

        if self._play_context.become is False and play_context.become is True:
            auth_pass = play_context.become_pass
            self._cliconf._on_authorize(passwd=auth_pass)

        elif self._play_context.become is True and not play_context.become:
            self._cliconf._on_deauthorize()

        self._play_context = play_context

    def _connect(self):
        """Connects to the device
        """
        if self._play_context.password and not self._play_context.private_key_file:
            C.PARAMIKO_LOOK_FOR_KEYS = False

        super(Connection, self)._connect()

        display.display('ssh connection completed successfully', log_only=True)

        self._shell = self.ssh.invoke_shell()
        self._shell.settimeout(self._play_context.timeout)

        network_os = self._play_context.network_os
        if not network_os:
            if not network_os:
                for cls in cliconf_loader.all(class_only=True):
                    network_os = cls.guess_network_os(self.ssh)
                    if network_os:
                        break

        if not network_os:
            raise AnsibleConnectionFailure(
                'unable to determine device network os.  Please configure '
                'ansible_network_os value'
            )

        self._cliconf = cliconf_loader.get(network_os, self)
        if not self._cliconf:
            raise AnsibleConnectionFailure('unable to load cliconf for network_os %s' % network_os)

        self._rpc.add(self._cliconf)

        display.display('loaded cliconf plugin for network_os %s' % network_os, log_only=True)

        self.receive()

        display.display('firing event: on_open_shell()', log_only=True)
        self._cliconf._on_open_shell()

        if getattr(self._play_context, 'become', None):
            display.display('firing event: on_authorize', log_only=True)
            auth_pass = self._play_context.become_pass
            self._cliconf._on_authorize(passwd=auth_pass)

        self._connected = True
        display.display('ssh session negotiation has completed successfully', log_only=True)

    @ensure_connect
    def open_shell(self):
        if not self._shell:
            display.display('attempting to open shell to device', log_only=True)
            self._shell = self.ssh.invoke_shell()
            display.display('self._shell %s' % self._shell, log_only=True)
            self._shell.settimeout(self._play_context.timeout)

            self.receive()

            display.display('firing event: on_open_shell()', log_only=True)
            if self._shell:
                self._cliconf._on_open_shell()

            if getattr(self._play_context, 'become', None):
                display.display('firing event: on_authorize', log_only=True)
                auth_pass = self._play_context.become_pass
                self._cliconf.on_authorize(passwd=auth_pass)

            display.display('shell successfully opened', log_only=True)
        return b'ok'

    def close(self):
        """Close the active connection to the device
        """
        display.display("closing ssh connection to device", log_only=True)
        if self._shell:
            display.display("firing event: on_close_shell()", log_only=True)
            self._cliconf._on_close_shell()

        if self._shell:
            self._shell.close()
            self._shell = None
            display.display("cli session is now closed", log_only=True)

        super(Connection, self).close()

        self._connected = False
        display.display("ssh connection has been closed successfully", log_only=True)

    def receive(self, command=None, prompts=None, answer=None):
        """Handles receiving of output from command
        """
        recv = BytesIO()
        handled = False

        self._matched_prompt = None

        while True:
            data = self._shell.recv(256)

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
        """Sends the command to the device in the opened shell
        """
        try:
            self._history.append(command)
            self._shell.sendall('%s\r' % command)
            if send_only:
                return
            return self.receive(command, prompts, answer)

        except (socket.timeout, AttributeError) as exc:
            display.display(traceback.format_exc(), log_only=True)
            raise AnsibleConnectionFailure("timeout trying to send command: %s" % command.strip())

    def _strip(self, data):
        """Removes ANSI codes from device response
        """
        for regex in self._cliconf.terminal_ansi_re:
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
        if not isinstance(prompts, list):
            prompts = [prompts]
        prompts = [re.compile(r, re.I) for r in prompts]
        for regex in prompts:
            match = regex.search(resp)
            if match:
                self._shell.sendall('%s\r' % answer)
                return True

    def _sanitize(self, resp, command=None):
        """Removes elements from the response before returning to the caller
        """
        cleaned = []
        for line in resp.splitlines():
            if (command and line.startswith(command.strip())) or self._matched_prompt.strip() in line:
                continue
            cleaned.append(line)
        return b"\n".join(cleaned).strip()

    def _find_prompt(self, response):
        """Searches the buffered response for a matching command prompt"""
        errored_response = None
        for regex in self._cliconf.terminal_stderr_re:
            if regex.search(response):
                errored_response = response
                break

        for regex in self._cliconf.terminal_stdout_re:
            match = regex.search(response)
            if match:
                self._matched_pattern = regex.pattern
                self._matched_prompt = match.group()
                if not errored_response:
                    return True

        if errored_response:
            raise AnsibleConnectionFailure(errored_response)

    def alarm_handler(self, signum, frame):
        """Alarm handler raised in case of command timeout """
        display.display('closing shell due to sigalarm', log_only=True)
        self.close()

    def exec_command(self, input):
        """Executes the cmd on in the shell and returns the output

        The method accepts two forms of cmd.  The first form is as a byte
        string that represents the RPC method to be executed. The
        second form is as a utf8 JSON byte string with additional keywords.

        Keywords supported for cmd:
            * command - the command string to execute
            * prompt - the expected prompt generated by executing command
            * answer - the string to respond to the prompt with
            * sendonly - bool to disable waiting for response
            * method - RPC method to be executed

        :arg cmd: the byte string that represents the command to be executed
            which can be a single command or a json encoded string.
        :returns: a tuple of (return code, stdout, stderr).  The return
            code is an integer and stdout and stderr are byte strings
        """
        req = {b'jsonrpc': b'2.0', b'id': str(uuid.uuid4()),b'method': b'get'}
        try:
            out = json.loads(input)
            if b'method' in out:
                req[b'method'] = out[b'method']
            params = {}
            for key in (b'command', b'prompts', b'answer', b'sendonly'):
                if key in out:
                    params[key] = out[key]
            if params:
                req[b'params'] = params
        except (ValueError, TypeError):
            req[b'method'] = input

        try:
            reply = json.loads(self._exec_rpc(req))
            if reply[b'id'] != req[b'id']:
                error_reply = self.internal_error('Invaild id received')
                return 1, b'', to_bytes(error_reply['error'])

            return 0, to_bytes(reply['result']), b''

        except (AnsibleConnectionFailure, ValueError) as exc:
            # FIXME: Feels like we should raise this rather than return it
            return (1, b'', to_bytes(exc))
