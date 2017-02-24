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

from . import models, email
from .app import app
from ..config import config


@click.group()
def cli():
  pass


@cli.command()
@click.option('-h', '--host')
@click.option('-p', '--port', type=int)
@click.option('-d', '--debug/--no-debug', default=None)
@click.option('--prefix')
def run(host, port, debug, prefix):
  if host is None:
    host = config['upmd.host']
  if port is None:
    port = int(os.getenv('', int(config['upmd.port'])))
  if debug is None:
    debug = (config['upmd.debug'].lower().strip() == 'true')
  if prefix is not None:
    config['upmd.prefix'] = prefix
  app.run(host=host, port=port, debug=debug)


@cli.command()
def drop():
  reply = input('Do you really want to drop all data in the database? ')
  if reply  in ('y', 'yes'):
    print('Okay..')
    models.User.drop_collection()
    models.Package.drop_collection()
    models.PackageVersion.drop_collection()
  else:
    print('Better so.')


@cli.command()
@click.argument('from_', 'from')
@click.argument('to')
def testmail(from_, to):
  part = email.MIMEText('This is a test email')
  part['From'] = from_
  part['To'] = to
  part['Subject'] = 'Test email'
  s = email.make_smtp()
  s.sendmail(from_, [to], part.as_string())
  s.quit()


if __name__ == '__main__':
  cli()
