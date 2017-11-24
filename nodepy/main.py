"""
The Node.py command-line interface.
"""

from nodepy.utils import pathlib, path
from nodepy.loader import PythonModule
import argparse
import code
import functools
import os
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


def install_pmd(ctx):
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
  ctx.resolver.paths.extend(map(pathlib.Path, args.nodepy_path))
  ctx.localimport.path.extend(args.python_path)

  # Create the module in which we run the REPL or the command
  # specified via -c.
  if args.c or not args.request:
    filename = nodepy.utils.path.VoidPath('<repl>')
    directory = pathlib.Path.cwd()
    repl_module = nodepy.base.Module(ctx, None, filename, directory)
    repl_module.init()
    repl_module.loaded = True

  with ctx.enter():
    if args.pmd:
      install_pmd(ctx)
    if args.c:
      six.exec_(args.c, vars(repl_module.namespace))
    if args.request:
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
      ctx.main_module = repl_module
      code.interact('', local=vars(repl_module.namespace))


if __name__ == '__main__':
  sys.exit(main())
