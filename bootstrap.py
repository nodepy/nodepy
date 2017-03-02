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
Bootstrap the installation of the PPYM, installing all Python dependencies
into `nodepy_modules/.pymodules`.
"""

if require.main != module:
  raise RuntimeError('bootstrap must not be required')

import click
import json
import os
import pip.commands
import shutil
import sys


@click.command()
@click.option('--install', is_flag=True, help="Install PPYM after bootstrapping "
    "and clean up the bootstrapped nodepy_modules/ directory.")
@click.option('-g', '--global', 'global_', is_flag=True, help="Install PPYM globally.")
@click.option('-U', '--upgrade', is_flag=True)
def main(install, global_, upgrade):
  """
  Bootstrap the PPYM installation.
  """

  existed_before = os.path.isdir('nodepy_modules')

  print("Bootstrapping PPYM dependencies with Pip ...")
  with open(os.path.join(__directory__, 'package.json')) as fp:
    package = json.load(fp)

  cmd = ['--target', 'nodepy_modules/.pymodules']
  for key, value in package['python-dependencies'].items():
    cmd.append(key + value)

  res = pip.commands.InstallCommand().main(cmd)
  if res != 0:
    print('error: Pip installation failed')
    sys.exit(res)

  if install:
    # This is necessary on Python 2.7 (and possibly other versions) as
    # otherwise importing the newly installed Python modules will fail.
    sys.path_importer_cache.clear()

    print("Installing PPYM {} ...".format('globally' if global_ else 'locally'))
    cmd = ['install']
    if upgrade:
      cmd.append('--upgrade')
    if global_:
      cmd.append('--global')
    cmd.append(__directory__)
    require('./index').main(cmd, standalone_mode=False)

    if not existed_before:
      print('Cleaning up bootstrap modules directory ...')
      shutil.rmtree('nodepy_modules')


main()
