# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import distutils.sysconfig
import json
import os
import sys

try:
  import pip._internal.locations as pip_locations
except ImportError:
  import pip.locations as pip_locations

from nodepy.context import Context

PACKAGE_MANIFEST = Context.package_manifest
MODULES_DIRECTORY = Context.modules_directory
PIP_DIRECTORY = Context.pipprefix_directory
PROGRAM_DIRECTORY = os.path.join(os.path.dirname(PIP_DIRECTORY), 'bin')
LINK_SUFFIX = Context.link_suffix


def is_virtualenv():
  if hasattr(sys, 'real_prefix'):
    return True
  if hasattr(sys, 'base_prefix'): # Python 3+ only
    return sys.prefix != sys.base_prefix
  return False


def get_directories(location, auto_upgrade=True):
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

  If *auto_upgrade* is #True (which it is by default), `'global'` will
  automatically be upgraded into `'root'` inside a virtual environment.
  """

  assert location in ('local', 'global', 'root')
  if auto_upgrade and location == 'global' and is_virtualenv():
    location = 'root'

  local = pip_locations.distutils_scheme('', prefix=PIP_DIRECTORY)
  if location == 'local':
    return {
      'packages': MODULES_DIRECTORY,
      'bin': PROGRAM_DIRECTORY,
      'pip_prefix': local['data'],
      'pip_bin': local['scripts'],
      'pip_lib': local['purelib']
    }

  user = (location == 'global')
  scheme = pip_locations.distutils_scheme('', user=user)

  return {
    # Install Node.py modules near the site-packages.
    'packages': os.path.join(os.path.dirname(scheme['purelib']), 'nodepy-modules'),
    'bin': scheme['scripts'],
    'pip_prefix': scheme['data'],
    # Re-use Pip's script and site-packages directory.
    'pip_bin': scheme['scripts'],
    'pip_lib': scheme['purelib']
  }


def pip_locations_for(directory):
  """
  Returns a dictionary that contains the `pip_prefix`, `pip_bin` and
  `pip_lib` members as returned by #get_directories() but for a directory
  that contains the pip data (i.e. `myproject/.nodepy`).
  """

  scheme = pip_locations.distutils_scheme('', prefix=PIP_DIRECTORY)
  return {
    'pip_prefix': os.path.join(directory, scheme['data']),
    'pip_bin': os.path.join(directory, scheme['scripts']),
    'pip_lib': os.path.join(directory, scheme['purelib'])
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
    dist_info = os.path.join(dirname, fn)
    version = fn[len(module) + 1:-len('.dist-info')]

    # Load the metadata.json.
    fn = os.path.join(dist_info, 'metadata.json')
    if not os.path.isfile(fn):
      # TODO: Don't show if no verbose output is desired.
      print('warning: file \'{}\' does not exist'.format(fn))
      continue
    with open(fn) as fp:
      data =json.load(fp)
    data['.dist-info'] = dist_info

    # Load the top-level file.
    fn = os.path.join(dist_info, 'top_level.txt')
    if os.path.isfile(fn):
      with open(fn) as fp:
        data['top_level'] = fp.read().splitlines()
    else:
      data['top_level'] = []

    return data

  return None


def cfgvars(dev):
  """
  Determines the variables available to the `cfg(...)` feature in the
  manifest file. Note that the `dev` flag is not intended to be used
  transitively, thus it is not automatically determined but must instead
  be explicitly specified, and usually it is only specified for the
  main package that is being installed.
  """

  vars = {}
  if dev: vars['dev'] = True
  else: vars['prod'] = True
  if os.name == 'nt': vars['win32'] = True
  elif sys.platform.startswith('darwin'): vars['darwin'] = True
  elif sys.platform.startswith('linux'): vars['linux'] = True
  else: vars['unknown'] = True
  return vars
