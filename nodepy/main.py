"""
The Node.py command-line interface.
"""

from nodepy.utils import pathlib
import argparse
import code
import nodepy
import sys

VERSION = 'Node.py v{} [{} {}]'.format(
  nodepy.__version__, nodepy.runtime.implementation, sys.version)

parser = argparse.ArgumentParser()
parser.add_argument('request', nargs='?')


def main(argv=None):
  args = parser.parse_args(argv)
  ctx = nodepy.context.Context()

  if args.request:
    ctx.main_module = ctx.resolve(args.request)
    ctx.load_module(ctx.main_module)
  else:
    ctx.main_module = nodepy.base.Module(ctx, None, pathlib.Path('<repl>'), pathlib.Path.cwd())
    ctx.main_module.init()
    ctx.main_module.loaded = True
    code.interact(VERSION, local=vars(ctx.main_module.namespace))


if __name__ == '__main__':
  main()
