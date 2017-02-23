# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__all__ = ['config', 'filename']

import configparser
import os
from .upm.logging import logger

config = {}
filename = os.path.expanduser(os.getenv('UPYTHON_CONFIG', '~/.upython/config'))

if os.path.isfile(filename):
  parser = configparser.SafeConfigParser()
  parser.read([filename])
  for section in parser.sections():
    for option, value in parser.items(section):
      config[section + '.' + option] = value

# Default values for upython.
config.setdefault('upython.prefix', os.getenv('UPYTHON_PREFIX', '~/.upython'))
config.setdefault('upython.local_packages_dir', 'upython_packages')
config['upython.prefix'] = os.path.expanduser(config['upython.prefix'])

# Default values for upm.
config.setdefault('upm.registry', 'https://upmpy.org')
config.setdefault('upm.author', '')
config.setdefault('upm.license', '')

# Default values for upmd.
config.setdefault('upmd.host', 'localhost')
config.setdefault('upmd.port', '8000')
config.setdefault('upmd.debug', 'false')
config.setdefault('upmd.prefix', '~/.upython/registry')
config.setdefault('upmd.mongodb_host', 'localhost')
config.setdefault('upmd.mongodb_port', '27017')
config.setdefault('upmd.mongodb_database', 'upm_registry')
config['upmd.prefix'] = os.path.expanduser(config['upmd.prefix'])
