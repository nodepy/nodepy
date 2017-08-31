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
Bootstrap the installation of the NPPM, installing all Python dependencies
into `nodepy_modules/.pip`.
"""

if require.main != module:
  raise RuntimeError('bootstrap must not be required')

import argparse
import os
import shutil
import subprocess
import sys

import brewfix from './lib/brewfix'


def main(args=None):
  parser = argparse.ArgumentParser(description='Bootstrap the NPPM installation.')
  parser.add_argument('--root', action='store_true',
      help='Install NPPM into the Python root prefix.')
  parser.add_argument('--global', dest='global_', action='store_true',
      help='Install NPPM into the user-local prefix directory.')
  parser.add_argument('--upgrade', action='store_true',
      help='Overwrite an existing NPPM installation.')
  parser.add_argument('--develop', action='store_true',
      help='Install NPPM in develop mode, creating a .nodepy-link instead '
        'of copying the NPPM package files.')
  args = parser.parse_args(sys.argv[1:] if args is None else args)

  existed_before = os.path.isdir('nodepy_modules')
  print("Bootstrapping NPPM dependencies with Pip ...")
  package = require('./package.json')

  # We would like to use Pip --prefix, but there seems to be a Bug on Windows
  # that lets installations fail (see nodepym/NPPM#9).
  if os.name == 'nt':
    site_packages = 'Lib/site-packages'
  else:
    site_packages = 'lib/python{}.{}/site-packages'.format(*sys.version_info)
  cmd = ['--target', 'nodepy_modules/.pip/' + site_packages]
  for key, value in package['python-dependencies'].items():
    cmd.append(key + value)

  print('$ pip install', ' '.join(cmd))
  with brewfix():
    # We use a subprocess here as otherwise we run into nodepy/nodepy#48,
    # "underlying buffer has been detached" when Pip uses the spinner or
    # download progress bar.
    res = subprocess.call([sys.executable, '-m', 'pip', 'install'] + cmd)
  if res != 0:
    print('error: Pip installation failed')
    sys.exit(res)

  # This is necessary on Python 2.7 (and possibly other versions) as
  # otherwise importing the newly installed Python modules will fail.
  sys.path_importer_cache.clear()

  cmd = ['install', '--ignore-installed']
  if args.upgrade:
    cmd.append('--upgrade')
  if args.global_:
    cmd.append('--global')
  if args.root:
    cmd.append('--root')
  if args.develop:
    cmd.append('--develop')
  cmd.append(__directory__)

  # We need to set this option as otherwise the dependencies that we JUST
  # bootstrapped will be considered as already satsified, even though they
  # will not be after NPPM was installed in root or global level.
  cmd.append('--pip-separate-process')

  print("Installing NPPM ({}) ...".format(' '.join(cmd)))
  require('./index').main(cmd, standalone_mode=False)

  local = (not args.global_ and not args.root)
  if not local and not existed_before and os.path.isdir('nodepy_modules'):
    print('Cleaning up bootstrap modules directory ...')
    shutil.rmtree('nodepy_modules')


main()
