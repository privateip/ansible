#
# This code is part of Ansible, but is an independent component.
#
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# (c) 2017 Red Hat, Inc.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import os
import time

from ansible.module_utils._text import to_text, to_native
from ansible.module_utils.network.common.config import NetworkConfig, dumps
from ansible.module_utils.network.common.utils import to_list, ComplexList
from ansible.module_utils.six import iteritems
from ansible.module_utils.urls import fetch_url
from ansible.module_utils.network.eos import eos_argument_spec, eos_provider_spec


def load_params(module):
    provider = module.params.get('provider') or dict()
    for key, value in iteritems(provider):
        if key in eos_argument_spec:
            if module.params.get(key) is None and value is not None:
                module.params[key] = value

def to_command(module, commands):
    transform = ComplexList(dict(
        command=dict(key=True),
        output=dict(default='json'),
        prompt=dict(type='list'),
        answer=dict(type='list'),
        sendonly=dict(type='bool', default=False),
        check_all=dict(type='bool', default=False),
    ), module)
    return transform(to_list(commands))


class Eapi(object):

    __rpc__ = ['get_config', 'edit_config', 'get_capabilities', 'get', 'enable_response_logging', 'disable_response_logging']

    def __init__(self, module):
        self._module = module
        self._enable = None
        self._session_support = None
        self._device_configs = {}

        load_params(module)

        host = module.params['provider']['host']
        port = module.params['provider']['port']

        self._module.params['url_username'] = self._module.params['username']
        self._module.params['url_password'] = self._module.params['password']

        if module.params['provider']['use_ssl']:
            proto = 'https'
        else:
            proto = 'http'

        module.params['validate_certs'] = module.params['provider']['validate_certs']

        self._url = '%s://%s:%s/command-api' % (proto, host, port)

        if module.params['auth_pass']:
            self._enable = {'cmd': 'enable', 'input': module.params['auth_pass']}
        else:
            self._enable = 'enable'

    @property
    def supports_sessions(self):
        if self._session_support:
            return self._session_support
        response = self.send_request(['show configuration sessions'])
        self._session_support = 'error' not in response
        return self._session_support


    def get_capabilities(self):
        result = {}
        rpc_list = ['commit', 'discard_changes', 'get_diff', 'run_commands', 'supports_sessions']
        result['rpc'] = self.__rpc__ + rpc_list
        result['device_info'] = self.get_device_info()
        result['device_operations'] = self.get_device_operations()
        result.update(self.get_option_values())
        result['network_api'] = 'eapi'
        return self._module.jsonify(result)

    def get_option_values(self):
        return {
            'format': ['text', 'json'],
            'diff_match': ['line', 'strict', 'exact', 'none'],
            'diff_replace': ['line', 'block', 'config'],
            'output': ['text', 'json']
        }

    def _request_builder(self, commands, output, reqid=None):
        params = dict(version=1, cmds=commands, format=output)
        return dict(jsonrpc='2.0', id=reqid, method='runCmds', params=params)

    def get_device_info(self):
        device_info = {}
        device_info['network_os'] = 'eos'
        data = self.get('show version | json')
        device_info['network_os_version'] = data['version']
        device_info['network_os_model'] = data['modelName']
        data = self.get('show hostname | json')
        device_info['network_os_hostname'] = data['hostname']
        return device_info

    def get_device_operations(self):
        return {
            'supports_diff_replace': True,
            'supports_commit': True if self.supports_sessions else False,
            'supports_rollback': False,
            'supports_defaults': False,
            'supports_onbox_diff': True if self.supports_sessions else False,
            'supports_commit_comment': False,
            'supports_multiline_delimiter': False,
            'supports_diff_match': True,
            'supports_diff_ignore_lines': True,
            'supports_generate_diff': False if self.supports_sessions else True,
            'supports_replace': True if self.supports_sessions else False
        }

    def send_request(self, commands, output='text'):
        commands = to_list(commands)

        if self._enable:
            commands.insert(0, self._enable)

        body = self._request_builder(commands, output)
        data = self._module.jsonify(body)

        headers = {'Content-Type': 'application/json-rpc'}
        timeout = self._module.params['timeout']
        use_proxy = self._module.params['provider']['use_proxy']

        response, headers = fetch_url(
            self._module, self._url, data=data, headers=headers,
            method='POST', timeout=timeout, use_proxy=use_proxy
        )

        if headers['status'] != 200:
            self._module.fail_json(**headers)

        try:
            data = response.read()
            response = self._module.from_json(to_text(data, errors='surrogate_then_replace'))
        except ValueError:
            self._module.fail_json(msg='unable to load response from device', data=data)

        if self._enable and 'result' in response:
            response['result'].pop(0)

        return response

    def run_commands(self, commands, check_rc=True):
        """Runs list of commands on remote device and returns results
        """
        output = None
        queue = list()
        responses = list()

        commands = to_command(self._module, commands)

        def _send(commands, output):
            response = self.send_request(commands, output=output)
            if 'error' in response:
                err = response['error']
                self._module.fail_json(msg=err['message'], code=err['code'])
            return response['result']

        for item in to_list(commands):
            if self.is_json(item['command']):
                item['command'] = str(item['command']).replace('| json', '')
                item['output'] = 'json'

            if output and output != item['output']:
                responses.extend(_send(queue, output))
                queue = list()

            output = item['output'] or 'json'
            queue.append(item['command'])

        if queue:
            responses.extend(_send(queue, output))

        for index, item in enumerate(commands):
            try:
                responses[index] = responses[index]['output'].strip()
            except KeyError:
                pass

        return responses

    def get(self, command):
        resp = self.run_commands(command)
        return resp[0]

    def get_config(self, flags=None):
        """Retrieves the current config from the device or cache
        """
        flags = [] if flags is None else flags

        cmd = 'show running-config '
        cmd += ' '.join(flags)
        cmd = cmd.strip()

        try:
            return self._device_configs[cmd]
        except KeyError:
            out = self.send_request(cmd)
            cfg = str(out['result'][0]['output']).strip()
            self._device_configs[cmd] = cfg
            return cfg

    def configure(self, commands):
        """Sends the ordered set of commands to the device
        """
        cmds = ['configure terminal']
        cmds.extend(commands)

        responses = self.send_request(commands)
        if 'error' in responses:
            err = responses['error']
            self._module.fail_json(msg=err['message'], code=err['code'])

        return responses[1:]

    def load_config(self, config, commit=False, replace=False):
        """Loads the configuration onto the remote devices

        If the device doesn't support configuration sessions, this will
        fallback to using configure() to load the commands.  If that happens,
        there will be no returned diff or session values
        """
        use_session = os.getenv('ANSIBLE_EOS_USE_SESSIONS', True)
        try:
            use_session = int(use_session)
        except ValueError:
            pass

        if not all((bool(use_session), self.supports_sessions)):
            if commit:
                return self.configure(config)
            else:
                self._module.warn("EOS can not check config without config session")
                result = {'changed': True}
                return result

        session = 'ansible_%s' % int(time.time())
        result = {'session': session}
        commands = ['configure session %s' % session]

        if replace:
            commands.append('rollback clean-config')

        commands.extend(config)

        response = self.send_request(commands)
        if 'error' in response:
            commands = ['configure session %s' % session, 'abort']
            self.send_request(commands)
            err = response['error']
            error_text = []
            for data in err['data']:
                error_text.extend(data.get('errors', []))
            error_text = '\n'.join(error_text) or err['message']
            self._module.fail_json(msg=error_text, code=err['code'])

        commands = ['configure session %s' % session, 'show session-config diffs']
        if commit:
            commands.append('commit')
        else:
            commands.append('abort')

        response = self.send_request(commands, output='text')
        diff = response['result'][1]['output']
        if len(diff) > 0:
            result['diff'] = diff

        return result

    edit_config = load_config

    # get_diff added here to support connection=local and transport=eapi scenario
    def get_diff(self, candidate, running=None, diff_match='line', diff_ignore_lines=None, path=None, diff_replace='line'):
        diff = {}

        # prepare candidate configuration
        candidate_obj = NetworkConfig(indent=3)
        candidate_obj.load(candidate)

        if running and diff_match != 'none' and diff_replace != 'config':
            # running configuration
            running_obj = NetworkConfig(indent=3, contents=running, ignore_lines=diff_ignore_lines)
            configdiffobjs = candidate_obj.difference(running_obj, path=path, match=diff_match, replace=diff_replace)

        else:
            configdiffobjs = candidate_obj.items

        configdiff = dumps(configdiffobjs, 'commands') if configdiffobjs else ''
        diff['config_diff'] = configdiff if configdiffobjs else {}
        return diff

    def is_json(self, cmd):
        return to_native(cmd, errors='surrogate_then_replace').endswith('| json')
