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
The Node.py command-line interface.
"""

from nodepy.utils import path
from nodepy.loader import PythonModule
import argparse
import code
import functools
import os
import pathlib2 as pathlib
import pdb
import nodepy
import six
import sys

try:
  from urllib.parse import urlparse
except ImportError:
  from urlparse import urlparse

VERSION = 'nodepy {}\n[{} {}]'.format(
  nodepy.__version__, nodepy.runtime.implementation, sys.version.replace('\n', ''))

parser = argparse.ArgumentParser()
parser.add_argument('request', nargs='...')
parser.add_argument('-c')
parser.add_argument('--maindir')
parser.add_argument('--version', action='store_true')
parser.add_argument('--pymain', action='store_true')
parser.add_argument('--pmd', action='store_true')
parser.add_argument('--keep-arg0', action='store_true')
parser.add_argument('--nodepy-path', action='append', default=[])
parser.add_argument('--python-path', action='append', default=[])


class EntryModule(nodepy.loader.PythonModule):

  def run_with_exec_handler(self, handler):
    self._exec_code = lambda code: handler()
    self.load()

  # Overrides

  def _load_code(self):
    return None

  def _init_extensions(self):
    pass


def check_pmd_envvar():
  """
  Checks the value of the `NODEPY_PMD` environment variable. If it's an
  integer, it will be decrement by one. If the value falls below one, then
  the variable is unset so that future child processes can't inherit it.
  If the value is anything other than a string, it will be left unchanged.
  """

  value = os.environ.get('NODEPY_PMD', '')
  try:
    level = int(value)
  except ValueError:
    level = None

  if level is not None and level <= 0:
    value = ''
  elif level is not None and level <= 1:
    os.environ.pop('NODEPY_PMD', '')
  elif level is not None:
    os.environ['NODEPY_PMD'] = str(level - 1)

  return bool(value)


def enable_post_mortem_debugger(ctx):
  """
  Installs the post-mortem debugger which calls #Context.breakpoint().
  """

  @functools.wraps(sys.excepthook)
  def wrapper(type, value, traceback):
    ctx.breakpoint(traceback)
    return wrapper.__wrapped__(type, value, traceback)

  sys.excepthook = wrapper


def main(argv=None):
  args = parser.parse_args(argv)
  args.nodepy_path.insert(0, '.')
  if args.version:
    print(VERSION)
    return 0

  args.pmd = check_pmd_envvar() or args.pmd
  sys.argv = [sys.argv[0]] + args.request[1:]

  maindir = pathlib.Path(args.maindir) if args.maindir else pathlib.Path.cwd()
  ctx = nodepy.context.Context(maindir)

  # Update the module search path.
  args.nodepy_path.insert(0, ctx.modules_directory)  # TODO:  Use the nearest available .nodepy/modules directory?
  ctx.resolver.paths.extend(x for x in map(pathlib.Path, args.nodepy_path))
  ctx.localimport.path.extend(args.python_path)

  # This is the entry-point module. It will set up the Python sys.path
  # for the current working directory when executed.
  entry_module = EntryModule(
    ctx, None, nodepy.utils.path.VoidPath('<entry>'), pathlib.Path.cwd()
  )
  entry_module.init()

  with ctx.enter():
    if args.pmd:
      enable_post_mortem_debugger(ctx)
    if args.c:
      def exec_handler():
        six.exec_(args.c, vars(entry_module.namespace))
    if args.request:
      def exec_handler():
        try:
          filename = path.urlpath.make(args.request[0])
        except ValueError:
          filename = args.request[0]
        ctx.main_module = ctx.resolve(filename)
        if not args.keep_arg0:
          sys.argv[0] = str(ctx.main_module.filename)
        ctx.main_module.init()
        if args.pymain:
          ctx.main_module.namespace.__name__ = '__main__'
        ctx.load_module(ctx.main_module, do_init=False)
    elif not args.c:
      ctx.main_module = entry_module
      def exec_handler():
        code.interact('', local=vars(entry_module.namespace))
    entry_module.run_with_exec_handler(exec_handler)


if __name__ == '__main__':
  sys.exit(main())
