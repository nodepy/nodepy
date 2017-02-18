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
import os

from . import Cpm, AddRequire, PackageNotFound, NoSuchModule
from .utils import refstring
from .utils.config import parse_config
from sys import exit


def load_module(cpm, ref):
  """
  Loads a module from a package specified by the #refstring.Ref *ref* and
  executes it. Returns the loaded module. Expected errors are handle and
  cause the application to exit gracefully.
  """

  if ref.package:
    try:
      package = cpm.load_package(ref.package, ref.version)
    except PackageNotFound as exc:
      print('error: Package "{}" not found'.format(exc))
      exit(1)
  else:
    package = cpm.load_main_package()

  try:
    module = package.load_module(ref.module)
  except NoSuchModule as exc:
    print('error:', exc)
    exit(1)

  return module


@click.group()
@click.pass_context
def cli(ctx):
  try:
    config = parse_config(os.path.expanduser('~/.cpm/config'))
  except FileNotFoundError as exc:
    config = {}
  config['cpm:prefix'] = os.path.expanduser(config.get('cpm:prefix', '~/.cpm'))
  config.setdefault('cpm:localModulePrefix', 'cpm_modules')

  # Set up the Loader object for all subcommands.
  cpm = Cpm(config['cpm:prefix'], config['cpm:localModulePrefix'])
  cpm.loader.before_exec.append(AddRequire(cpm))
  for exc in cpm.update_cache():
    print('warning:', exc)

  ctx.obj = cpm


@cli.command()
@click.argument('ref', metavar=refstring.spec, required=False)
@click.argument('args', metavar='[ARGS]...', nargs=-1)
@click.pass_obj
def run(cpm, ref, args):
  ref = refstring.parse(ref or '')
  module = load_module(cpm, ref)
  module.exec_()
  if ref.member:
    function = getattr(module.namespace, ref.member, None)
    if not callable(function):
      print('error: "{}" is not a function'.format(refstring.join(
          package.name, package.version, module.name, ref.member)))
      exit(1)
    function(args)
