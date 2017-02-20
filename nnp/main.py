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

import click
import code
import os
import sys
import traceback
from sys import exit
from . import __version__
from .core.manifest import PackageManifest, NotAPackageDirectory
from .core.package import Module, Package
from .core.session import Session
from .core.executor import ExecuteError
from .config import get_config


def _get_up_package(directory):
  prev = None  # Necessary to find root on Windows
  directory = os.path.abspath(directory)
  while directory and directory != prev:
    try:
      return PackageManifest.parse(directory)
    except NotAPackageDirectory:
      pass
    prev = directory
    directory = os.path.dirname(directory)
  return None


def _make_session(local_dir=None):
  config = get_config()
  local_dir = os.path.join(local_dir or '.', config['nnp:local_packages_dir'])
  return Session(prefix=config['nnp:prefix'], local_packages=local_dir)



def run(filename=None, package=None, local_dir=None, args=None):
  if filename and package:
    print('error: filename and --package can not be specified at the same time')
    exit(1)
  elif not filename and not package:
    raise ValueError('neither filename nor package specified')

  session = _make_session(local_dir)
  if filename:
    manifest = _get_up_package(os.path.dirname(filename))
    if manifest:
      package = session.add_package(manifest)
      module = package.load_module_from_filename(filename)
    else:
      module = Module(None, filename)
  else:
    module = session.require(package, exec_=False)
    filename = module.filename

  if args is not None:
    sys.argv = [filename]
    sys.argv.extend(args)

  try:
    session.exec_module(module)
  except ExecuteError as exc:
    if isinstance(exc.exc_info[1], SystemExit):
      raise exc.exc_info[1]
    traceback.print_exception(*exc.exc_info)
    exit(1)


def run_interactive(local_dir=None):
  session = _make_session(local_dir)
  module = Module(None, None)
  session.on_init_module(module)
  code.interact('', local=vars(module.namespace))


@click.command()
@click.argument('filename', required=False)
@click.argument('args', nargs=-1)
@click.option('-p', '--package')
@click.option('-l', '--local-dir')
@click.option('-v', '--version', is_flag=True)
def cli(filename, args, package, local_dir, version):
  if version:
    print('nnp {} on Python {}'.format(__version__, sys.version))
    return
  if not filename and not package:
    assert not args
    run_interactive(local_dir)
  else:
    run(filename, package, local_dir, args)
