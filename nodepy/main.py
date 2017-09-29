"""
The Node.py command-line interface.
"""

from nodepy.utils import pathlib
import argparse
import code
import nodepy
import sys

VERSION = 'node.py {} [{} {}]'.format(
  nodepy.__version__, nodepy.runtime.implementation, sys.version)

parser = argparse.ArgumentParser()
parser.add_argument('request', nargs='...')
parser.add_argument('--version', action='store_true')


def main(argv=None):
  args = parser.parse_args(argv)
  if args.version:
    print(VERSION)
    return 1

  sys.argv = [sys.argv[0]] + args.request[1:]
  ctx = nodepy.context.Context()
  with ctx.enter():
    if args.request:
      ctx.main_module = ctx.resolve(args.request[0])
      ctx.load_module(ctx.main_module)
    else:
      ctx.main_module = nodepy.base.Module(ctx, None, pathlib.Path('<repl>'), pathlib.Path.cwd())
      ctx.main_module.init()
      ctx.main_module.loaded = True
      code.interact(VERSION, local=vars(ctx.main_module.namespace))


if __name__ == '__main__':
  sys.exit(main())
