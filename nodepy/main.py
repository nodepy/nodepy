"""
The Node.py command-line interface.
"""

from nodepy.utils import pathlib
from nodepy.loader import PythonModule
import argparse
import code
import nodepy
import sys

try:
  from urllib.parse import urlparse
except ImportError:
  from urllib2 import urlparse

VERSION = 'node.py {} [{} {}]'.format(
  nodepy.__version__, nodepy.runtime.implementation, sys.version)

parser = argparse.ArgumentParser()
parser.add_argument('request', nargs='...')
parser.add_argument('--version', action='store_true')
parser.add_argument('--keep-arg0', action='store_true')
parser.add_argument('--nodepy-path', action='append', default=[])
parser.add_argument('--python-path', action='append', default=[])


def main(argv=None):
  args = parser.parse_args(argv)
  args.nodepy_path.insert(0, '.')
  if args.version:
    print(VERSION)
    return 1

  sys.argv = [sys.argv[0]] + args.request[1:]

  ctx = nodepy.context.Context()
  ctx.resolvers[0].paths.extend(map(pathlib.Path, args.nodepy_path))
  ctx.localimport.path.extend(args.python_path)
  with ctx.enter():
    if args.request:
      url_info = urlparse(args.request[0])
      if url_info.scheme in ('http', 'https'):
        # Create a new module from a UrlPath filename.
        filename = nodepy.utils.UrlPath(args.request[0])
        module = PythonModule(ctx, None, filename)
        ctx.modules[module.filename] = module
        ctx.main_module = module
      else:
        ctx.main_module = ctx.resolve(args.request[0])
      if not args.keep_arg0:
        sys.argv[0] = str(ctx.main_module.filename)
      ctx.load_module(ctx.main_module)
    else:
      ctx.main_module = nodepy.base.Module(ctx, None, pathlib.Path('<repl>'), pathlib.Path.cwd())
      ctx.main_module.init()
      ctx.main_module.loaded = True
      code.interact(VERSION, local=vars(ctx.main_module.namespace))


if __name__ == '__main__':
  sys.exit(main())
