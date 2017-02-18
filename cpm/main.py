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

from . import Loader, Finder, AddRequire, PackageNotFound, NoSuchModule
from .config import parse_config
from .utils import refstring
from sys import exit


def load_module(loader, ref, exec_=True):
  """
  Loads a module from a package specified by the #refstring.Ref *ref* and
  executes it. Returns the loaded module. Expected errors are handle and
  cause the application to exit gracefully.
  """

  if ref.package:
    try:
      package = loader.load_package(ref.package, ref.version)
    except PackageNotFound as exc:
      print('error: Package "{}" not found'.format(exc))
      exit(1)
  else:
    if not loader.finder.main_package:
      print('error: no main package found')
      exit(1)
    package = loader.add_package(loader.finder.main_package)

  try:
    module = package.load_module(ref.module)
  except NoSuchModule as exc:
    print('error:', exc)
    exit(1)

  if exec_:
    loader.exec_module(module)
  return module


@click.group()
@click.pass_context
def cli(ctx):
  try:
    config = parse_config()
  except FileNotFoundError as exc:
    config = {}
  config['cpm:prefix'] = os.path.expanduser(config.get('cpm:prefix', '~/.cpm'))
  config.setdefault('cpm:localModulePrefix', 'cpm_modules')

  # Set up the Loader object for all subcommands.
  finder = Finder([config['cpm:prefix'], config['cpm:localModulePrefix']])
  loader = Loader()
  loader.before_exec.append(AddRequire(loader))
  for exc in loader.update_cache():
    print('warning:', exc)

  ctx.obj = loader


@cli.command()
@click.argument('ref', metavar=refstring.spec, required=False)
@click.argument('args', metavar='[ARGS]...', nargs=-1)
@click.pass_obj
def run(loader, ref, args):
  ref = refstring.parse(ref or '')
  module = load_module(loader, ref)
  if ref.function:
    function = getattr(module.namespace, ref.function, None)
    if not callable(function):
      print('error: "{}" is not a function'.format(refstring.join(
          package.name, package.version, module.name, ref.function)))
      raise SystemExit(1)
    function(args)
