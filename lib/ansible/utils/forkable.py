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


import os
import sys

def do_fork():
    '''
    Does the required double fork for a daemon process. Based on
    http://code.activestate.com/recipes/66012-fork-a-daemon-process-on-unix/
    '''
    try:
        pid = os.fork()
        if pid > 0:
            return pid

        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            out_file = open('/dev/null', 'ab+')
            err_file = open('/dev/null', 'ab+', 0)
            dev_null = open('/dev/null', 'r')

            os.dup2(out_file.fileno(), sys.stdout.fileno())
            os.dup2(err_file.fileno(), sys.stderr.fileno())
            os.dup2(dev_null.fileno(), sys.stdin.fileno())

            return pid
        except OSError as e:
            sys.exit(1)
    except OSError as e:
        sys.exit(1)

