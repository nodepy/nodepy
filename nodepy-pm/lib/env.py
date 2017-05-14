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

import distutils.sysconfig
import json
import os
import pip.locations
import sys


def is_virtualenv():
  if hasattr(sys, 'real_prefix'):
    return True
  if hasattr(sys, 'base_prefix'): # Python 3+ only
    return sys.prefix != sys.base_prefix
  return False


def get_directories(location):
  """
  Returns a dictionary that contains information on the install location of
  Node.py packages. The dictionary contains the following keys:

  - packages
  - bin
  - pip_bin

  Only when *location* is `'local'` or `'global'`, the following keys are
  available:

  - pip_prefix
  - pip_lib
  """

  assert location in ('local', 'global', 'root')
  if location == 'local':
    scheme = pip.locations.distutils_scheme('', prefix='nodepy_modules/.pip')
    return {
      'packages': 'nodepy_modules',
      'bin': 'nodepy_modules/.bin',
      'pip_prefix': scheme['data'],
      'pip_bin': scheme['scripts'],
      'pip_lib': scheme['purelib']
    }
  else:
    user = (location == 'global')
    scheme = pip.locations.distutils_scheme('', user=user)
    return {
      'packages': os.path.join(os.path.dirname(scheme['purelib']), 'nodepy_modules'),
      'bin': scheme['scripts'],
      'pip_prefix': scheme['data'],
      'pip_bin': scheme['scripts'],
      'pip_lib': scheme['purelib']
    }


def get_python_install_type():
  """
  Returns a string with information about this Python installation. Possible
  return values are

  - `'root'` for a root-type installation
  - `'user'` for a user-type installation (eg. AppData/Local/Programs/Python
    on Windows)
  - `'virtual'` for a virtual environment-type installation
  """

  if is_virtualenv():
    return 'virtual'
  # If the executable is inside the current user's home directory, we
  # consider this to be a user-type installation.
  home = os.path.expanduser('~')
  try:
    rel = os.path.relpath(sys.prefix, home)
  except ValueError:
    pass
  else:
    if not rel.startswith(os.curdir) and not rel.startswith(os.pardir):
      return 'user'
  return 'root'


def get_module_dist_info(module, pythonpath=None):
  """
  Finds a Python module in the *pythonpath* and returns the distribution
  information stored by Pip in the respective `.dist-info` directory. If
  the module can not be found, #None will be returned.

  Note that the *module* name does not necessarily reflect the name of the
  Python module name that is used on `import`s, but instead the name of the
  module on PyPI and as defined in the `setup.py` script.
  """

  module = module.replace('-', '_').lower()

  if not pythonpath:
    pythonpath = sys.path
  sosuffix = distutils.sysconfig.get_config_var('SO')
  for dirname in sys.path:
    if not os.path.isdir(dirname): continue
    for fn in os.listdir(dirname):
      if not fn.endswith('.dist-info'): continue
      if not fn.lower().startswith(module + '-'): continue
      break
    else:
      continue
    version = fn[len(module) + 1:-len('.dist-info')]
    fn = os.path.join(dirname, fn, 'metadata.json')
    if not os.path.isfile(fn):
      # TODO: Don't show if no verbose output is desired.
      print('warning: file \'{}\' does not exist'.format(fn))
      continue
    with open(fn) as fp:
      return json.load(fp)

  return None
