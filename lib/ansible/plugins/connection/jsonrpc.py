# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2015, 2017 Toshio Kuratomi <tkuratomi@ansible.com>
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

DOCUMENTATION = '''
    connection: jsonrpc
    short_description: execute on controller using rpc calls
    description:
        - This connection plugin allows ansible to execute tasks on the
          Ansible 'controller' instead of on a remote host. It allows connection
          plugins to provide a persistent connection that supports rpc calls
    author: ansible (@core)
    version_added: 2.5
    notes:
        - The remote user is ignored, the user with which the ansible CLI was executed is used instead.
'''

import os
import sys
import json
import fcntl
import signal
import socket
import datetime
import time
import traceback
import errno

from ansible.plugins.loader import connection_loader
from ansible import constants as C

from ansible.module_utils._text import to_bytes, to_text
from ansible.module_utils.connection import send_data, recv_data
from ansible.utils.path import unfrackpath, makedirs_safe
from ansible.errors import AnsibleConnectionFailure
from ansible.plugins.connection.local import Connection as ConnectionBase
from ansible.utils.forkable import do_fork


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class Connection(ConnectionBase):
    ''' RPC based connections '''

    transport = 'jsonrpc'

    def __init__(self, *args, **kwargs):
        self._objects = set()
        super(Connection, self).__init__(*args, **kwargs)

    def register_object(self, obj):
        self._objects.add(obj)

    def exec_rpc(self, request):
        method = request.get('method')

        if method.startswith('rpc.') or method.startswith('_'):
            error = self.invalid_request()
            return json.dumps(error)

        params = request.get('params')
        setattr(self, '_identifier', request.get('id'))
        args = []
        kwargs = {}

        if all((params, isinstance(params, list))):
            args = params
        elif all((params, isinstance(params, dict))):
            kwargs = params

        rpc_method = None

        if method in ('shutdown', 'reset'):
            rpc_method = getattr(self, 'shutdown')

        else:
            for obj in self._objects:
                rpc_method = getattr(obj, method, None)
                if rpc_method:
                    break

        if not rpc_method:
            error = self.method_not_found()
            response = json.dumps(error)
        else:
            try:
                result = rpc_method(*args, **kwargs)
            except Exception as exc:
                display.vvv(traceback.format_exc(), host=self._play_context.remote_addr)
                error = self.internal_error(data=to_text(exc, errors='surrogate_then_replace'))
                response = json.dumps(error)
            else:
                if isinstance(result, dict) and 'jsonrpc' in result:
                    response = result
                else:
                    response = self.response(result)

                response = json.dumps(response)

        delattr(self, '_identifier')
        return response

    def listen(self, socket_path):
        setattr(self, 'socket_path', socket_path)

        display.vvvv('control socket path is %s' % socket_path, host=self._play_context.remote_addr)

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.socket_path)
        self.socket.listen(1)

        display.vvvv('local socket is set to listening', host=self._play_context.remote_addr)

    def run(self):
        try:
            while True:
                signal.signal(signal.SIGALRM, self.connect_timeout)
                signal.alarm(C.PERSISTENT_CONNECT_TIMEOUT)

                display.vvvv('socket waiting for new connection', host=self._play_context.remote_addr)
                (s, addr) = self.socket.accept()
                display.vvvv('incoming request accepted on persistent socket', host=self._play_context.remote_addr)
                signal.alarm(0)

                while True:
                    data = recv_data(s)
                    if not data:
                        break

                    signal.signal(signal.SIGALRM, self.request_timeout)
                    signal.alarm(self._play_context.timeout)

                    req = json.loads(data)
                    resp = self.exec_rpc(req)
                    signal.alarm(0)

                    send_data(s, to_bytes(resp))

                s.close()

        except Exception as e:
            # socket.accept() will raise EINTR if the socket.close() is called
            if hasattr(e, 'errno'):
                if e.errno != errno.EINTR:
                    display.debug(traceback.format_exc())
            else:
                display.vvvv(str(e), host=self._play_context.remote_addr)
                display.debug(traceback.format_exc())

        finally:
            # when done, close the connection properly and cleanup
            # the socket file so it can be recreated
            self.shutdown()

    def connect_timeout(self, signum, frame):
        display.vvv('persistent connection idle timeout triggered, timeout value is %s secs' % C.PERSISTENT_CONNECT_TIMEOUT, host=self._play_context.remote_addr)
        self.shutdown()

    def request_timeout(self, signum, frame):
        display.vvv('command timeout triggered, timeout value is %s secs' % self._play_context.timeout, host=self._play_context.remote_addr)
        self.shutdown()

    def shutdown(self):
        """ Shuts down the local domain socket
        """
        display.vvv('shutdown persistent connection requested for host %s' % self._play_context.remote_addr, host=self._play_context.remote_addr)

        if not os.path.exists(self.socket_path):
            display.vvv('persistent connection is not active', host=self._play_context.remote_addr)
            return

        try:
            if self.socket:
                display.vvv('closing local listener', host=self._play_context.remote_addr)
                self.socket.close()
            if self.connection:
                display.vvv('closing the connection', host=self._play_context.remote_addr)
                self.connection.close()

        except:
            pass

        finally:
            if os.path.exists(self.socket_path):
                display.vvv('removing the local control socket', host=self._play_context.remote_addr)
                os.remove(self.socket_path)

        display.vvv('shutdown complete', host=self._play_context.remote_addr)

    def start_connection(self, play_context):
        """ Must be implemented by the subclass
        """
        raise NotImplementedError

    def start(self, play_context):
        """ Called to initiate the connect to the remote device
        """
        ssh = connection_loader.get('ssh', class_only=True)
        cp = ssh._create_control_path(play_context.remote_addr, play_context.port, play_context.remote_user)

        # create the persistent connection dir if need be and create the paths
        # which we will be using later
        tmp_path = unfrackpath(C.PERSISTENT_CONTROL_PATH_DIR)
        makedirs_safe(tmp_path)

        lock_path = unfrackpath("%s/.ansible_pc_lock" % tmp_path)
        socket_path = unfrackpath(cp % dict(directory=tmp_path))

        # if the socket file doesn't exist, spin up the daemon process
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.lockf(lock_fd, fcntl.LOCK_EX)

        if not os.path.exists(socket_path):
            pid = do_fork()
            if pid == 0:
                rc = 0
                try:
                    self.start_connection(play_context)
                    self.listen(socket_path)
                except AnsibleConnectionFailure as exc:
                    display.vvvv(str(exc), host=play_context.remote_addr)
                    display.debug(traceback.format_exc())
                    rc = 1
                except Exception as exc:
                    display.vvvv('failed to create control socket for host %s' % play_context.remote_addr, host=play_context.remote_addr)
                    display.debug(traceback.format_exc())
                    rc = 1
                fcntl.lockf(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                if rc == 0:
                    self.run()
                sys.exit(rc)

        timeout = play_context.timeout
        while bool(timeout):
            if os.path.exists(socket_path):
                display.vvvv('connected to local socket in %s seconds' % (play_context.timeout - timeout), play_context.remote_addr)
                break
            time.sleep(1)
            timeout -= 1
        else:
            raise AnsibleConnectionFailure('timeout waiting for local socket', play_context.remote_addr)

        setattr(self, 'socket_path', socket_path)
        return socket_path

    def header(self):
        return {'jsonrpc': '2.0', 'id': self._identifier}

    def response(self, result=None):
        response = self.header()
        response['result'] = result or 'ok'
        return response

    def error(self, code, message, data=None):
        response = self.header()
        error = {'code': code, 'message': message}
        if data:
            error['data'] = data
        response['error'] = error
        return response

    # json-rpc standard errors (-32768 .. -32000)
    def parse_error(self, data=None):
        return self.error(-32700, 'Parse error', data)

    def method_not_found(self, data=None):
        return self.error(-32601, 'Method not found', data)

    def invalid_request(self, data=None):
        return self.error(-32600, 'Invalid request', data)

    def invalid_params(self, data=None):
        return self.error(-32602, 'Invalid params', data)

    def internal_error(self, data=None):
        return self.error(-32603, 'Internal error', data)


