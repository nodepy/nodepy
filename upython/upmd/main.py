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

from .app import app
from ..config import config


@click.command()
@click.option('-h', '--host')
@click.option('-p', '--port', type=int)
@click.option('-d', '--debug/--no-debug', default=None)
@click.option('--prefix')
def cli(host, port, debug, prefix):
  if host is None:
    host = config['upmd.host']
  if port is None:
    port = int(os.getenv('', int(config['upmd.port'])))
  if debug is None:
    debug = (config['upmd.debug'].lower().strip() == 'true')
  if prefix is not None:
    config['upmd.prefix'] = prefix
  app.run(host=host, port=port, debug=debug)
