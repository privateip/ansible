# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2012-17, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: template
    author: Michael DeHaan <michael.dehaan@gmail.com>
    version_added: "0.9"
    short_description: retrieve contents of file after templating with Jinja2
    description:
      - this is mostly a noop, to be used as a with_list loop when you do not want the content transformed in any way.
    options:
      _terms:
        description: list of files to template
      convert_data:
        type: bool
        description: whether to convert YAML into data. If False, strings that are YAML will be left untouched.
      variable_start_string:
        description: The string marking the beginning of a print statement.
        default: '{{'
        version_added: '2.8'
        type: str
      variable_end_string:
        description: The string marking the end of a print statement.
        default: '}}'
        version_added: '2.8'
        type: str
"""

EXAMPLES = """
- name: show templating results
  debug:
    msg: "{{ lookup('template', './some_template.j2') }}"

- name: show templating results with different variable start and end string
  debug:
    msg: "{{ lookup('template', './some_template.j2', variable_start_string='[%', variable_end_string='%]') }}"
"""

RETURN = """
_raw:
   description: file(s) content after templating
"""

import importlib

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):

        for term in terms:
            module_name = 'ansible.module_utils.network.%s.providers.cli.config.%s' % (variables['ansible_network_os'], term)
            module = importlib.import_module(module_name)

            config = {'hostname': 'localhost', 'domain_name': 'redhat.com'}
            params = {'config': config, 'operation': 'merge'}
            provider = module.Provider(params)

            resp = provider.render()
            resp = '\n'.join(resp)

        return [resp]
