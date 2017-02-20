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
import sys
import traceback
from sys import exit
from .core.package import Module
from .core.session import Session
from .core.executor import ExecuteError


@click.command()
@click.argument('filename', required=False)
@click.argument('args', nargs=-1)
@click.option('-p', '--package')
def cli(filename, package, args):
  if not filename and not package:
    # TODO: Enter interactive mode
    print('error: interactive mode not implemented')
    exit(1)
  elif filename and package:
    print('error: filename and --package can not be specified at the same time')
    exit(1)

  session = Session()
  if filename:
    module = Module(None, filename)
  else:
    module = session.require(package, exec_=False)
    filename = module.filename

  sys.argv = [filename]
  sys.argv.extend(args)

  try:
    session.exec_module(module)
  except ExecuteError as exc:
    traceback.print_exception(*exc.exc_info)
