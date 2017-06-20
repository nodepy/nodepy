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

from __future__ import print_function
from operator import itemgetter
from six.moves import input
from sys import exit

import click
import collections
import functools
import getpass
import json
import nodepy
import os
import pip.req
import six

import manifest from './lib/manifest'
import semver from './lib/semver'
import refstring from './lib/refstring'
import config from './lib/config'
import logger from './lib/logger'
import _install from './lib/install'
import registry from './lib/registry'
import PackageLifecycle from './lib/package-lifecycle'
import { is_virtualenv, get_module_dist_info } from './lib/env'


class Less(object):
  # http://stackoverflow.com/a/3306399/791713
  def __init__(self, num_lines):
    self.num_lines = num_lines
  def __ror__(self, other):
    s = six.text_type(other).split("\n")
    for i in range(0, len(s), self.num_lines):
      print("\n".join(s[i:i+self.num_lines]))
      input("Press <Enter> for more")


def get_install_location(global_, root):
  if global_ and root:
    print('Error: -g,--global and --root can not be used together')
    exit(1)
  elif global_:
    if is_virtualenv():
      print('Note: detected virtual environment, upgrading -g,--global to --root')
      return 'root'
    return 'global'
  elif root:
    return 'root'
  else:
    return 'local'


def get_installer(global_, root, upgrade, pip_separate_process,
                  pip_use_target_option, recursive, verbose=False):
  location = get_install_location(global_, root)
  return _install.Installer(upgrade=upgrade, install_location=location,
      pip_separate_process=pip_separate_process,
      pip_use_target_option=pip_use_target_option, recursive=recursive,
      verbose=verbose)


def exit_with_return(func):
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    res = func(*args, **kwargs)
    exit(res)
  return wrapper

@click.group(help="""
  Node.py Package Manager (on {})
  """.format(nodepy.VERSION))
def main():
  if not config['registry'].startswith('https://'):
    logger.warning('config value `registry` is not an HTTPS url ({})'
        .format(config['registry']))


@main.command()
def version():
  """
  Print the nppm and Node.py version.
  """

  print('nppm-{} (on {})'.format(require('./package.json')['version'], nodepy.VERSION))


@main.command()
@click.argument('packages', nargs=-1)
@click.option('-e', '--develop', help='Install a package in development mode.', multiple=True)
@click.option('-py', '--python', help='Specify a package to install via Pip.', multiple=True)
@click.option('-epy', '--develop-python', help='Specify a package to install via Pip in develop mode.', multiple=True)
@click.option('-U', '--upgrade', is_flag=True)
@click.option('-g', '--global/--local', 'global_', is_flag=True)
@click.option('-I', '--ignore-installed', is_flag=True,
    help='Passes the same option to Pip.')
@click.option('-P', '--packagedir', default='.',
    help='The directory to read/write the package.json to/from.')
@click.option('--root', is_flag=True)
@click.option('--recursive', is_flag=True,
    help='Satisfy dependencies of already satisfied dependencies.')
@click.option('--pip-separate-process', is_flag=True)
@click.option('--pip-use-target-option', is_flag=True,
    help='Use --target instead of --prefix when installing dependencies '
      'via Pip. This is to circumvent a Bug in Pip where installing with '
      '--prefix fails. See nodepy/ppym#9.')
@click.option('--info', is_flag=True)
@click.option('--dev/--production', 'dev', default=None,
    help='Specify whether to install development dependencies or not. The '
      'default value depends on the installation type (--dev when no packages '
      'are specified, --production otherwise).')
@click.option('--save', is_flag=True,
    help='Save the installed dependencies into the "dependencies" or '
      '"python-dependencies" field, respectively.')
@click.option('--save-dev', is_flag=True,
    help='Save the installed dependencies into the "dev-dependencies" or '
      '"dev-python-dependencies" field, respectively.')
@click.option('--save-ext', is_flag=True,
    help='Save the installed dependencies into the "extensions" field. '
      'Installed Python modules are ignored for this one. Implies --save')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_context
@exit_with_return
def install(ctx, packages, develop, python, develop_python, upgrade, global_,
            ignore_installed, packagedir, root, recursive, info, dev,
            pip_separate_process, pip_use_target_option, save, save_dev,
            save_ext, verbose):
  """
  Installs one or more Node.Py or Pip packages.
  """

  packagefile = os.path.join(packagedir, 'package.json')

  if save_ext:
    if save_dev:
      print('Warning: --save-ext should not be combined with --save-dev')
      print('  Extensions must be available during runtime.')
    else:
      # Implying --save
      save = True

  if save and save_dev:
    print('Error: decide for either --save or --save-dev')
    return 1
  if save or save_dev:
    if not os.path.isfile(packagefile):
      print('Error: can not --save or --save-dev without a package.json')
      return 1
    with open(packagefile) as fp:
      package_json = json.load(fp, object_pairs_hook=collections.OrderedDict)

  if dev is None:
    dev = not packages

  installer = get_installer(global_, root, upgrade, pip_separate_process,
      pip_use_target_option, recursive, verbose)
  installer.ignore_installed = ignore_installed
  if info:
    for key in sorted(installer.dirs):
      print('{}: {}'.format(key, installer.dirs[key]))
    return 0

  if not any((packages, develop, python, develop_python)):
    success = installer.install_dependencies_for(manifest.parse(packagefile), dev=dev)
    if not success:
      return 1
    installer.relink_pip_scripts()
    return 0

  save_deps = []
  def handle_package(package, develop=False):
    if package.startswith('git+'):
      success, package_info = installer.install_from_git(package[4:])
      if success:
        save_deps.append((package_info[0], package))
    elif os.path.isdir(package):
      success = installer.install_from_directory(package, develop, dev=dev)[0]
    elif os.path.isfile(package):
      success = installer.install_from_archive(package, dev=dev)[0]
    else:
      ref = refstring.parse(package)
      selector = ref.version or semver.Selector('*')
      success, package_info = installer.install_from_registry(six.text_type(ref.package), selector, dev=dev)
      if success:
        save_deps.append((package_info[0], '~' + str(package_info[1])))
    if not success:
      ctx.fail('Installation failed')

  python_deps = {}
  python_additional_install = []
  def handle_python_package(package, develop=False):
    package = os.path.expanduser(package)
    if os.path.isdir(package) or os.path.isfile(package):
      if develop:
        python_additional_install.append('-e')
      python_additional_install.append(package)
    else:
      try:
        spec = pip.req.InstallRequirement.from_line(package)
      except (pip.exceptions.InstallationError, pip._vendor.packaging.requirements.InvalidRequirement) as exc:
        return ctx.fail(exc)
      if (save or save_dev) and not spec.req:
        return ctx.fail("'{}' is not something we can install via NPPM with --save/--save-dev".format(package[3:]))
      if spec.req:
        python_deps[spec.req.name] = str(spec.req.specifier)
      else:
        if develop:
          python_additional_install.append('-e')
        python_additional_install.append(str(spec))

  # Parse and install Python packages.
  for package in python:
    handle_python_package(package)
  for package in develop_python:
    handle_python_package(package, develop=True)
  if (python_deps or python_additional_install):
    if not installer.install_python_dependencies(
        python_deps, args=python_additional_install):
      print('Installation failed')
      return 1

  # Parse and install Node.py packages.
  for package in packages:
    handle_package(package)
  for package in develop:
    handle_package(package, develop=True)

  installer.relink_pip_scripts()

  if (save or save_dev) and save_deps:
    field = 'dependencies' if save else 'dev-dependencies'
    data = package_json.get(field, {})
    print('Saving {}...'.format(field))
    for key, value in save_deps:
      print('  "{}": "{}"'.format(key, value))
      data[key] = value

    data = sorted(data.items(), key=itemgetter(0))
    package_json[field] = collections.OrderedDict(data)

  if (save or save_dev) and python_deps:
    field = 'python-dependencies' if save else 'dev-python-dependencies'
    print("Saving {}...".format(field))
    data = package_json.get(field, {})
    for pkg_name, dist_info in installer.installed_python_libs.items():
      if not dist_info:
        print('warning: could not find .dist-info of module "{}"'.format(pkg_name))
        data[pkg_name] = ''
        print('  "{}": ""'.format(pkg_name))
      else:
        data[dist_info['name']] = '>=' + dist_info['version']
        print('  "{}": "{}"'.format(dist_info['name'], dist_info['version']))

    # Sort the data and insert it back into the package manifest.
    data = sorted(data.items(), key=itemgetter(0))
    package_json[field] = collections.OrderedDict(data)

  if save_ext and save_deps:
    extensions = package_json.setdefault('extensions', [])
    for ext_name in sorted(map(itemgetter(0), save_deps)):
      if ext_name not in extensions:
        extensions.append(ext_name)

  if (save or save_dev) and (save_deps or python_deps):
    with open(packagefile, 'w') as fp:
      json.dump(package_json, fp, indent=2)

  print()
  return 0


@main.command()
@click.argument('package')
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--root', is_flag=True)
@exit_with_return
def uninstall(package, global_, root):
  """
  Uninstall a module with the specified name from the local package directory.
  To uninstall the module from the global package directory, specify
  -g/--global.
  """

  location = get_install_location(global_, root)
  installer = _install.Installer(install_location=location)
  installer.uninstall(package)


@main.command()
@exit_with_return
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
@exit_with_return
def upload(filename, force, user, password, dry):
  """
  Upload a file to the current version to the registry. If the package does
  not already exist on the registry, it will be added to your account
  automatically. The first package that is uploaded must be the package
  source distribution that can be created with 'nppm dist'.
  """

  PackageLifecycle().upload(filename, user, password, force, dry)


@main.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-u', '--user')
@click.option('-p', '--password')
@click.option('--dry', is_flag=True)
@exit_with_return
def publish(force, user, password, dry):
  """
  Combination of `nppm dist` and `nppm upload`. Also invokes the `pre-publish`
  and `post-publish` scripts.
  """

  PackageLifecycle().publish(user, password, force, dry)


@main.command()
@click.option('--agree-tos', is_flag=True)
@click.option('--save', is_flag=True, help='Save username in configuration.')
@exit_with_return
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
@exit_with_return
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
    ('?Description', 'description', None),
    ('?Author (Name <Email>)', 'author', config.get('author')),
    ('?License', 'license', config.get('license')),
    ('?Main', 'main', None)
  ]

  results = collections.OrderedDict()
  for qu in questions:
    msg = qu[0]
    opt = msg.startswith('?')
    if opt: msg = msg[1:]
    if qu[2]:
      msg += ' [{}]'.format(qu[2])
    while True:
      reply = input(msg + '? ').strip() or qu[2]
      if reply or opt: break
    if reply and reply != '-':
      results[qu[1]] = reply

  reply = input('Do you want to use the require-import-syntax extension? [Y/n] ')
  if reply.lower() not in ('n', 'no', 'off'):
    results.setdefault('extensions', []).append('!require-import-syntax')
  else:
    reply = input('Do you want to use the require-unpack-syntax extension? [Y/n] ')
    if reply.lower() not in ('n', 'no', 'off'):
      results.setdefault('extensions', []).append('!require-unpack-syntax')

  with open(filename, 'w') as fp:
    json.dump(results, fp, indent=2)
    fp.write('\n')


@main.command()
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--root', is_flag=True)
@click.option('--pip', is_flag=True)
@exit_with_return
def bin(global_, root, pip):
  """
  Print the path to the bin directory.
  """

  location = get_install_location(global_, root)
  dirs = _install.get_directories(location)
  if pip:
    print(dirs['pip_bin'])
  else:
    print(dirs['bin'])


@main.command()
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--root', is_flag=True)
def dirs(global_, root):
  """
  Print install target directories.
  """

  location = get_install_location(global_, root)
  dirs = _install.get_directories(location)
  print('Packages:\t', dirs['packages'])
  print('Bin:\t\t', dirs['bin'])
  print('Pip Prefix:\t', dirs['pip_prefix'])
  print('Pip Bin:\t', dirs['pip_bin'])
  print('Pip Lib:\t', dirs['pip_lib'])


@main.command(context_settings={'ignore_unknown_options': True})
@click.argument('script')
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@exit_with_return
def run(script, args):
  """
  Run a script that is specified in the package.json.
  """
  if not PackageLifecycle().run(script, args):
    print("Error: no script '{}'".format(script))
    exit(1)


if require.main == module:
  main()
