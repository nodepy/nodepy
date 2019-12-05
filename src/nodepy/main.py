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


def get_stdlib_path():
  # Check if we're in a developer install.
  src_dir = os.path.normpath(__file__ + '/../..')
  develop = os.path.basename(src_dir) == 'src'
  if develop:
    return src_dir
  else:
    return os.path.join(sys.prefix, 'data', 'nodepy-runtime', 'stdlib')


def get_argument_parser(prog):
  parser = argparse.ArgumentParser(prog=prog, description=__doc__)
  parser.add_argument('--version', action='version', help='Print the version an exit.', version=VERSION)
  parser.add_argument('-C', '--context-dir', help='The Node.py context\'s main directory.')
  parser.add_argument('-D', '--post-mortem-debugger', action='store_true', help='Enable the post-mortem debugger.')
  parser.add_argument('-M', '--py-main', action='store_true', help='Set __name__ to __main__ in the main module.')
  parser.add_argument('-I', '--python-path', action='append', default=[], help='Additional Python search path.')
  parser.add_argument('-R', '--nodepy-path', action='append', default=[], help='Additional Node.py search path.')
  parser.add_argument('-c', '--eval', nargs='...', default=[], help='A snippet of code and arguments to run.')
  parser.add_argument('script', nargs='...', default=[], help='A script or module and arguments to run.')
  parser.add_argument('--no-override-argv0', action='store_true', help='Keep sys.argv[0] instead of overriding it with the module filename.')
  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  args.nodepy_path.insert(0, '.')
  args.nodepy_path.insert(0, get_stdlib_path())
  args.post_mortem_debugger = args.post_mortem_debugger or check_pmd_envvar()

  # Initialize the Node.py context.
  ctx = nodepy.context.Context(pathlib.Path(args.context_dir or '.'))
  args.nodepy_path.insert(0, ctx.modules_directory)  # TODO:  Use the nearest available .nodepy/modules directory?
  ctx.resolver.paths.extend(x for x in map(pathlib.Path, args.nodepy_path))
  ctx.localimport.path.extend(args.python_path)

  sys.argv = [sys.argv[0]] + (args.script or args.eval)[1:]

  # The entry module executes the script or code.
  entry_module = EntryModule(ctx, None,
    nodepy.utils.path.VoidPath('<entry>'), pathlib.Path.cwd())
  entry_module.init()

  with ctx.enter():
    if args.post_mortem_debugger:
      enable_post_mortem_debugger(ctx)
    if args.eval:
      def exec_handler():
        six.exec_(args.eval[0], vars(entry_module.namespace))
    elif args.script:
      def exec_handler():
        request = args.script[0]
        try:
          filename = path.urlpath.make(request)
        except ValueError:
          filename = request
        ctx.main_module = ctx.resolve(filename)
        if not args.no_override_argv0:
          sys.argv[0] = str(ctx.main_module.filename)
        ctx.main_module.init()
        if args.py_main:
          ctx.main_module.namespace.__name__ = '__main__'
        ctx.load_module(ctx.main_module, do_init=False)
    else:
      ctx.main_module = entry_module
      def exec_handler():
        code.interact('', local=vars(entry_module.namespace))
    entry_module.run_with_exec_handler(exec_handler)


if __name__ == '__main__':
  sys.exit(main())
