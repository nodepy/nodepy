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
import collections
import getpass
import json
import os
import nodepy
import six
import sys
import tarfile

from six.moves import input

manifest = require('./lib/manifest')
semver = require('./lib/semver')
refstring = require('./lib/refstring')
config = require('./lib/config')
logger = require('./lib/logger')
_install = require('./lib/install')
registry = require('./lib/registry')


class Less(object):
  # http://stackoverflow.com/a/3306399/791713
  def __init__(self, num_lines):
    self.num_lines = num_lines
  def __ror__(self, other):
    s = six.text_type(other).split("\n")
    for i in range(0, len(s), self.num_lines):
      print("\n".join(s[i:i+self.num_lines]))
      input("Press <Enter> for more")


class PackageLifecycle(object):

  def __init__(self, directory='.', dist_dir=None):
    if not dist_dir:
      dist_dir = os.path.join(directory, 'dist')
    self.manifest = manifest.parse(os.path.join(directory, 'package.json'))
    self.dist_dir = dist_dir

  def dist(self):
    self.manifest.run_script('pre-dist')
    filename = registry.get_package_archive_name(self.manifest.name,
        self.manifest.version)
    filename = os.path.join(self.dist_dir, filename)
    if not os.path.isdir(self.dist_dir):
      os.makedirs(self.dist_dir)

    print('Creating archive "{}"...'.format(filename))
    archive = tarfile.open(filename, 'w:gz')
    for filename, rel in _install.walk_package_files(self.manifest):
      print('  Adding "{}"...'.format(rel))
      archive.add(filename, rel)
    self.manifest.run_script('post-dist')
    print('Done!')
    return filename

  def upload(self, filename, user, password, force, dry):
    if not os.path.isfile(filename):
      print('error: "{}" does not exist'.format(filename))
      exit(1)

    # If the file looks like a package distribution archive of a different
    # version, let the user confirm that he/she really wants to upload the file.
    basename = os.path.basename(filename)
    if basename.startswith(self.manifest.identifier) and basename \
        != registry.get_package_archive_name(self.manifest.name, self.manifest.version):
      print('This looks a like a package distribution archive, but it ')
      print('does not match with the package\'s current version. Do you ')
      print('really want to upload this file? [y/n] ')
      reply = input().lower().strip()
      if reply not in ('y', 'yes'):
        exit(1)

    url = config['registry']
    user = user or config.get('username')
    if not user or not password:
      print('Credentials for', url)
    if not user:
      user = input('Username? ')
    else:
      print('Username?', user)
    if not password:
      password = getpass.getpass('Password? ')

    if dry:
      print('Not actually uploading things... (dry mode)')
    else:
      reg = registry.RegistryClient(url, user, password)
      msg = reg.upload(self.manifest.name, self.manifest.version, filename, force)
      print(msg)

  def publish(self, user, password, force, dry):
    self.manifest.run_script('pre-publish')
    filename = self.dist()
    self.upload(filename, user, password, force, dry)
    self.manifest.run_script('post-publish')


@click.group()
def main():
  if not config['registry'].startswith('https://'):
    logger.warning('config value `registry` is not an HTTPS url ({})'
        .format(config['registry']))


@main.command()
@click.argument('packages', nargs=-1)
@click.option('-e', '--develop', is_flag=True)
@click.option('-S', '--strict', is_flag=True)
@click.option('-U', '--upgrade', is_flag=True)
@click.option('-g', '--global/--local', 'global_', is_flag=True)
def install(packages, develop, strict, upgrade, global_):
  """
  Installs one or more packages.
  """

  installer = _install.Installer(upgrade=upgrade, global_=global_, strict=strict)
  if not packages:
    success = installer.install_dependencies_for(manifest.parse('package.json'))
    if not success:
      return 1
    installer.relink_pip_scripts()
    return 0

  for package in packages:
    if os.path.isdir(package):
      success = installer.install_from_directory(package, develop)
    elif os.path.isfile(package):
      success = installer.install_from_archive(package)
    else:
      ref = refstring.parse(package)
      selector = ref.version or semver.Selector('*')
      success = installer.install_from_registry(six.text_type(ref.package), selector)
    if not success:
      print('Installation failed')
      return 1

  installer.relink_pip_scripts()
  return 0


@main.command()
@click.argument('package')
@click.option('-g', '--global', 'global_', is_flag=True)
def uninstall(package, global_):
  """
  Uninstall a module with the specified name from the local package directory.
  To uninstall the module from the global package directory, specify
  -g/--global.
  """

  installer = _install.Installer(global_=global_)
  installer.uninstall(package)


@main.command()
def dist():
  """
  Create a .tar.gz distribution from the package.
  """

  PackageLifecycle().dist()


@main.command()
@click.argument('filename')
@click.option('-f', '--force', is_flag=True)
@click.option('-u', '--user')
@click.option('-p', '--password')
@click.option('--dry', is_flag=True)
def upload(filename, force, user, password, dry):
  """
  Upload a file to the current version to the registry. If the package does
  not already exist on the registry, it will be added to your account
  automatically. The first package that is uploaded must be the package
  source distribution that can be created with 'ppym dist'.
  """

  PackageLifecycle().upload(filename, force, user, password, dry)


@main.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-u', '--user')
@click.option('-p', '--password')
@click.option('--dry', is_flag=True)
def publish(force, user, password, dry):
  """
  Combination of `ppym dist` and `ppym upload`. Also invokes the `pre-publish`
  and `post-publish` scripts.
  """

  PackageLifecycle().publish(force, user, password, dry)


@main.command()
@click.option('--agree-tos', is_flag=True)
@click.option('--save', is_flag=True, help='Save username in configuration.')
def register(agree_tos, save):
  """
  Register a new user on the package registry.
  """

  reg = registry.RegistryClient(config['registry'])
  if not agree_tos:
    print('You have to agree to the Terms of Use before you can')
    print('register an account. Download and display terms now? [Y/n] ')
    reply = input().strip().lower() or 'yes'
    if reply not in ('yes', 'y'):
      print('Aborted.')
      return 0
    reg.terms() | Less(30)
    print('Do you agree to the above terms? [Y/n]')
    reply = input().strip().lower() or 'yes'
    if reply not in ('yes', 'y'):
      print('Aborted.')
      return 0

  username = input('Username? ')
  if len(username) < 3 or len(username) > 30:
    print('Username must be 3 or more characters.')
    return 1
  password = getpass.getpass('Password? ')
  if len(password) < 6 or len(password) > 64:
    print('Password must be 6 or more characters long.')
    return 1
  if getpass.getpass('Confirm Password? ') != password:
    print('Passwords do not match.')
    return 1
  email = input('E-Mail? ')
  # TODO: Validate email.
  if len(email) < 4:
    print('Invalid email.')
    return 1

  msg = reg.register(username, password, email)
  print(msg)

  if save:
    config['username'] = username
    config.save()
    print('Username saved in', config.filename)


@main.command()
@click.argument('directory', default='.')
def init(directory):
  """
  Initialize a new package.json.
  """

  filename = os.path.join(directory, 'package.json')
  if os.path.isfile(filename):
    print('error: "{}" already exists'.format(filename))
    return 1

  questions = [
    ('Package Name', 'name', None),
    ('Package Version', 'version', '1.0.0'),
    ('Author (Name <Email>)', 'author', config.get('author')),
    ('License', 'license', config.get('license'))
  ]

  results = collections.OrderedDict()
  for qu in questions:
    msg = qu[0]
    if qu[2]:
      msg += ' [{}]'.format(qu[2])
    while True:
      reply = input(msg + '? ').strip() or qu[2]
      if reply: break
    results[qu[1]] = reply

  results['dependencies'] = {}
  results['python-dependencies'] = {}
  results['dist'] = collections.OrderedDict()
  results['dist']['exclude_files'] = ['dist/*']

  with open(filename, 'w') as fp:
    json.dump(results, fp, indent=2)


@main.command()
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--pip', is_flag=True)
def bin(global_, pip):
  """
  Print the path to the bin directory.
  """

  dirs = _install.get_directories(global_)
  if pip:
    print(dirs.pip_bindir)
  else:
    print(dirs.bindir)


if require.main == module:
  main()
