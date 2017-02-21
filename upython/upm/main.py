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
import getpass
import tarfile

from ..config import config
from ..core import PackageManifest
from ..utils import refstring, semver
from .install import *
from .registry import Registry, RegistryError, make_package_archive_name


@click.group()
def cli():
  pass


@cli.command()
@click.argument('package')
@click.option('-g', '--global/--local', 'global_', is_flag=True)
def install(package, global_):
  registry = Registry(config['upm.registry'])

  if global_:
    e = os.path.expanduser
    dirs = {
      'packages': os.path.join(config['upython.prefix'], 'packages'),
      'bin': os.path.join(config['upython.prefix'], 'bin'),
      'python_modules': os.path.join(configp['upython.prefix'], 'pymodules'),
      'local_dir': None
    }
  else:
    dirs = {
      'packages': config['upython.local_packages_dir'],
      'bin': os.path.join(config['upython.local_packages_dir'], '.bin'),
      'python_modules': os.path.join(config['upython.local_packages_dir'], '.pymodules'),
      'local_dir': os.getcwd()
    }

  if os.path.isdir(package):
    install_from_directory(package, dirs, registry)
  elif os.path.isfile(package):
    install_from_archive(package, dirs, registry)
  else:
    ref = refstring.parse(package)
    selector = ref.version or semver.Selector('*')
    install_from_registry(ref.package, selector, dirs, registry)


@cli.command()
def dist():
  """
  Create a .tar.gz distribution from the package.
  """

  manifest = PackageManifest.parse('.')
  filename = os.path.join('dist', make_package_archive_name(manifest.name, manifest.version))
  if not os.path.isdir('dist'):
    os.mkdir('dist')
  print('Creating archive "{}"...'.format(filename))
  archive = tarfile.open(filename, 'w:gz')
  for filename, rel in walk_package_files(manifest):
    print('  Adding "{}"...'.format(rel))
    archive.add(filename, rel)
  print('Done!')


@cli.command()
@click.argument('filename')
@click.option('-f', '--force', is_flag=True)
def upload(filename, force):
  """
  Upload a file to the current version to the registry. If the package does
  not already exist on the registry, it will be added to your account
  automatically. The first package that is uploaded must be the package
  source distribution that can be created with 'upm dist'.
  """

  if not os.path.isfile(filename):
    print('error: "{}" does not exist'.format(filename))
    exit(1)
  manifest = PackageManifest.parse('.')

  url = config['upm.registry']
  username, password = config.get('upm.username'), config.get('upm.password')
  if not username or not password:
    print('Credentials for', url)
  if not username:
    username = input('Username: ')
  if not password:
    password = getpass.getpass()

  registry = Registry(url, username, password)
  try:
    registry.upload(manifest.name, manifest.version, filename, force)
  except RegistryError as exc:
    print('error: registry:', exc)
    exit(1)

  print('Done!')


@cli.command()
@click.option('-u', '--username')
@click.option('-p', '--password')
@click.option('-e', '--email')
def register(username, password, email):
  """
  Register a new user on the package registry.
  """

  if not username:
    username = input('Username: ')
  if not password:
    password = getpass.getpass()
  if not email:
    email = input('E-Mail: ')

  registry = Registry(config['upm.registry'])
  print(registry.register(username, password, email))
