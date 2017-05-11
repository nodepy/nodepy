# Copyright (c) 2017  Niklas Rosenstein
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
"""
This module provides a fix for brewed Python installations on macOS that,
by default, have the install "prefix" option set to a path in the users
Library directory. This option prevents successful Pip installations with
NPPM.

The fix will temporary set the install prefix option to an empty string in
the `~/.pydistutils.cfg` file, and then undo that change.
"""

import configparser
import contextlib
import os
import sys
is_virtualenv = require('./env').is_virtualenv()


@contextlib.contextmanager
def brewfix(prefix_dir='', force=False):
  if not force:
    if not sys.platform.startswith('darwin') or is_virtualenv:
      yield
      return

  print("Note: macOS detected, applying homebrew fix (see nodepy/ppym#9)")
  print("      [install] prefix={}".format(prefix_dir))
  filename = os.path.expanduser('~/.pydistutils.cfg')
  backupfile = filename + '.ppym-backup'
  parser = configparser.SafeConfigParser()

  if os.path.isfile(filename):
    parser.read([filename])
    os.rename(filename, backupfile)

  if not parser.has_section('install'):
    parser.add_section('install')

  parser.set('install', 'prefix', prefix_dir)
  with open(filename, 'w') as fp:
    parser.write(fp)

  try:
    yield
  finally:
    os.remove(filename)
    if os.path.isfile(backupfile):
      os.rename(backupfile, filename)


exports = brewfix
