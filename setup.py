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

try:
  import distlib.scripts
except ImportError:
  import pip._vendor.distlib.scripts
  distlib = pip._vendor.distlib

import contextlib
import json
import os
import pip
import setuptools
import sys

from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install

install_requires = ['colorama>=0.3.9', 'localimport>=1.5.1', 'six>=1.10.0', 'pip>=8.0.0', 'wheel>=0.29.0']

if 'develop' in sys.argv:
  name = 'node.py-' + sys.version[:3]
else:
  name = 'node.py'


def readme():
  """
  This helper function uses the `pandoc` command to convert the `README.md`
  into a `README.rst` file, because we need the long_description in ReST
  format. This function will only generate the `README.rst` if any of the
  `setup dist...` commands are used, otherwise it will return an empty string
  or return the content of the already existing `README.rst` file.
  """

  if os.path.isfile('README.md') and any('dist' in x for x in sys.argv[1:]):
    if os.system('pandoc -s README.md -o README.rst') != 0:
      print('-----------------------------------------------------------------')
      print('WARNING: README.rst could not be generated, pandoc command failed')
      print('-----------------------------------------------------------------')
      if sys.stdout.isatty():
        input("Enter to continue... ")
    else:
      print("Generated README.rst with Pandoc")

  if os.path.isfile('README.rst'):
    with open('README.rst') as fp:
      return fp.read()
  return ''


def install_deps():
  """
  Installs the dependencies of Node.py and package manager in a separate
  invokation of Pip. This is necessary so that we can install the PM after
  Node.py, because older versions of Pip do not establish a proper dependency
  installation order.
  """

  cmd = ['install'] + install_requires
  if 'PIPTARGETDIR' in os.environ:
    # When using the -t,--target option, this setup doesn't know about it
    # and will install the dependencies globally.
    cmd += ['-t', os.environ['PIPTARGETDIR']]

  print('Installing Node.py and Node.py-PM dependencies in a separate context ...')
  print("  Command: pip {}".format(' '.join(cmd)))

  res = pip.main(cmd)
  if res != 0:
    print("  Error: 'pip install' returned {}".format(res))
    sys.exit(res)


def install_pm(user, develop=False):
  """
  Executes the nppm `bootstrap` module to install it globally.
  """

  cmd = ['nppm/bootstrap', '--upgrade', '--global' if user else '--root']
  if develop:
    cmd.append('--develop')

  sys.path_importer_cache.clear()
  import nodepy
  try:
    nodepy.main(cmd)
  except SystemExit as exc:
    if exc.code != 0:
      raise


@contextlib.contextmanager
def hook_distlib_scriptmaker():
  """
  Hooks the #distlib.scripts.ScriptMaker._write_script() function, which in
  turn hooks the #os.path.splitext() function, to prevent the function from
  stripping the `.py` suffix from the `node.py` script.
  """

  ScriptMaker = distlib.scripts.ScriptMaker
  write_script = ScriptMaker._write_script
  splitext = os.path.splitext

  def new_splitext(path):
    if os.path.basename(path).startswith('node.py'):
      return path, '.py'
    return splitext(path)

  def new_write_script(self, *args, **kwargs):
    os.path.splitext = new_splitext
    try:
      return write_script(self, *args, **kwargs)
    finally:
      os.path.splitext = splitext

  ScriptMaker._write_script = new_write_script
  try:
    yield
  finally:
    ScriptMaker._write_script = write_script


class develop(_develop):
  def run(self):
    install_deps()
    with hook_distlib_scriptmaker():
      _develop.run(self)
    install_pm(develop=True, user=self.user)


class install(_install):
  def run(self):
    install_deps()
    with hook_distlib_scriptmaker():
      _install.run(self)
    install_pm(user=self.user)


setuptools.setup(
  name = name,
  version = '0.0.21',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = 'the Node.py python runtime and Node.py package manager',
  long_description = readme(),
  url = 'https://github.com/nodepy/nodepy',
  py_modules = ['nodepy'],
  install_requires = install_requires,
  entry_points = {
    # Note: We hook ScriptMaker._write_script to prevent it from
    # stripping the .py suffix.
    # Note: 'node.py' is deprecated for 'nodepy'.
    'console_scripts': [
      'nodepy{} = nodepy:main'.format(v)
      for v in ('', sys.version[0], sys.version[:3])
    ],
  },
  cmdclass = {
    'develop': develop,
    'install': install
  }
)
