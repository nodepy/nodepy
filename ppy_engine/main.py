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
from .core import Session, ResolveError


def run_interactive(session):
  raise NotImplementedError
  #module = Module(None, None)
  #session.on_init_module(module)
  #with session:
  #  code.interact('', local=vars(module.namespace))


@click.command()
@click.argument('filename', required=False)
@click.argument('args', nargs=-1)
@click.option('-v', '--version', is_flag=True)
def cli(filename, args, version):
  if version:
    print('ppy {} on Python {}'.format(__version__, sys.version))
    return

  session = Session()
  with session:
    if not filename:
      run_interactive(session)
      return
    module = session.resolve(filename, is_main=True)
    sys.argv = [module.filename] + list(args)
    module.load()
