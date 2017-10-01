#
# (c) 2017, Red Hat, Inc.
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
import traceback

from ansible import constants as C
from ansible.module_utils._text import to_text


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class JsonRpcServer(object):

    _objects = set()

    def handle_request(self, request):
        request = json.loads(request)

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
                display.vvv(traceback.format_exc(), host=self.connection._play_context.remote_addr)
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

    def register(self, obj):
        self._objects.add(obj)

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

