"""
The Node.py command-line interface.
"""

from nodepy.context import Context
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('request')


def main(argv=None):
  args = parser.parse_args(argv)
  ctx = Context()
  ctx.main_module = ctx.resolve(args.request)
  ctx.load_module(ctx.main_module)


if __name__ == '__main__':
  main()
