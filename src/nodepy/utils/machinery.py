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

"""
Utilities related to Pip or Python's standard package/modules.
"""

import os
import pathlib2 as pathlib
import six
import sys

try:
  reload
except NameError:
  try:
    from importlib import reload
  except ImportError:
    from imp import reload


def get_site_packages(prefix):
  """
  Returns the path to the `site-packages/` directory where Python modules
  are installed to via Pip given that the specified *prefix* is the same
  that was passed during the Pip installation.
  """

  if isinstance(prefix, str):
    prefix = pathlib.Path(prefix)

  if os.name == 'nt':
    lib = 'Lib'
  else:
    lib = 'lib/python{}.{}'.format(*sys.version_info)
  return prefix.joinpath(lib, 'site-packages')


def reload_pkg_resources(name='pkg_resources', insert_paths_index=None):
  """
  Cleanly reloads the `pkg_resources` module.
  """

  if name not in sys.modules:
    return

  path = sys.path[:]

  # Reload the module. However, reloading it will fail in Python 2 if we
  # don't clear its namespace beforehand due to the way it distinguishes
  # between Python 2 and 3. We still need to keep certain members, though.
  pkg_resources = sys.modules[name]

  # Clear all members, except for special ones.
  keep = {}
  for member in ['__name__', '__loader__', '__path__']:
    if hasattr(pkg_resources, member):
      keep[member] = getattr(pkg_resources, member)
  keep.setdefault('__name__', name)
  vars(pkg_resources).clear()
  vars(pkg_resources).update(keep)

  # Keep submodules.
  for mod_name, module in six.iteritems(sys.modules):
    if mod_name.startswith(name + '.') and mod_name.count('.') == 1:
      mod_name = mod_name.split('.')[1]
      setattr(pkg_resources, mod_name, module)

  # Reload pkg_resources.
  reload(pkg_resources)

  # Reloading pkg_resources will prepend new (or sometimes already
  # existing items) in sys.path. This will give precedence to system
  # installed packages rather than local packages that we added
  # through self.importer. Thus, we shall transfer all paths that are
  # newly introduced to sys.path and skip the rest. See nodepy/nodepy#49
  for p in sys.path:
    if p not in path:
      if insert_paths_index is None:
        path.append(p)
      else:
        path.insert(insert_paths_index, p)
  sys.path[:] = path
