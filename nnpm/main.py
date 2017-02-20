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
import tarfile

from nnp.utils import refstring, semver
from nnp.core.manifest import PackageManifest
from .install import install_from_directory, install_from_registry, install_from_archive, walk_package_files
from .config import get_config
from .registry import Registry, make_package_archive_name


@click.group()
def cli():
  pass


@cli.command()
@click.argument('package')
@click.option('-g', '--global/--local', 'global_', is_flag=True)
def install(package, global_):
  config = get_config()
  registry = Registry(config['nnpm:registry'])

  if global_:
    e = os.path.expanduser
    dirs = {
      'packages': os.path.join(config['nnp:prefix'], 'packages'),
      'bin': os.path.join(config['nnp:prefix'], 'bin'),
      'python_modules': os.path.join(configp['nnp:prefix'], 'pymodules'),
      'local_dir': None
    }
  else:
    dirs = {
      'packages': config['nnp:local_packages_dir'],
      'bin': os.path.join(config['nnp:local_packages_dir'], '.bin'),
      'python_modules': os.path.join(config['nnp:local_packages_dir'], '.pymodules'),
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
