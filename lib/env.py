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

import os
import sys


def is_virtualenv():
  if hasattr(sys, 'real_prefix'):
    return True
  if hasattr(sys, 'base_prefix'): # Python 3+ only
    return sys.prefix != sys.base_prefix
  return False


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
