# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function

import getpass
import nodepy.main
import os
import shlex
import six
import subprocess
import tarfile

from nodepy.utils import pathlib
from six.moves import input
from sys import exit

try:
  from shlex import quote as shlex_quote
except ImportError:
  from pipes import quote as shlex_quote

import nodepy

from .logger import logger
from . import env, install as _install, manifest as _manifest
from .registry import RegistryClient, get_package_archive_name


def find_nearest_bin_directory(path):
  for path in nodepy.utils.path.upiter(path):
    path = path.joinpath(env.PROGRAM_DIRECTORY)
    if path.is_dir():
      return path
  return None


class PackageLifecycle(object):

  @staticmethod
  def find_package_json(path):
    """
    Finds the first `nodepy.json` file in *path* or any of its parent
    directories and returns it. Returns #None if no file can be found.
    """

    if isinstance(path, six.string_types):
      path = pathlib.Path(path)
    for directory in nodepy.utils.path.upiter(path):
      fn = directory.joinpath(env.PACKAGE_MANIFEST)
      if fn.is_file():
        return str(fn)

  def __init__(self, context, directory='.', dist_dir=None, manifest=None, allow_no_manifest=False):
    if manifest is None:
      if not dist_dir:
        dist_dir = os.path.join(directory, 'dist')
      fn = self.find_package_json(directory)
      if not fn and not allow_no_manifest:
        print('Error: {} not found'.format(env.PACKAGE_MANIFEST))
        exit(1)
      if fn:
        manifest = _manifest.load(fn)

    self.context = context
    self.manifest = manifest
    self.dist_dir = dist_dir

  def dist(self):
    self.run('pre-dist', [], script_only=True)
    filename = get_package_archive_name(self.manifest['name'],
        self.manifest['version'])
    filename = os.path.join(self.dist_dir, filename)
    if not os.path.isdir(self.dist_dir):
      os.makedirs(self.dist_dir)

    print('Creating archive "{}"...'.format(filename))
    archive = tarfile.open(filename, 'w:gz')
    for name, rel in _install.walk_package_files(self.manifest):
      print('  Adding "{}"...'.format(rel))
      archive.add(name, rel)
    archive.close()
    self.run('post-dist', [], script_only=True)
    print('Done!')
    return filename

  def upload(self, filename, user, password, force, dry, registry):
    registry = RegistryClient.get(self.context.config, registry or 'default')
    if not os.path.isfile(filename):
      print('error: "{}" does not exist'.format(filename))
      exit(1)

    if user:
      registry.username = user
    if password:
      registry.password = password
    del user, password

    # If the file looks like a package distribution archive of a different
    # version, let the user confirm that he/she really wants to upload the file.
    basename = os.path.basename(filename)
    if basename.startswith(self.manifest.identifier) and basename \
        != registry.get_package_archive_name(self.manifest['name'], self.manifest['version']):
      print('This looks a like a package distribution archive, but it ')
      print('does not match with the package\'s current version. Do you ')
      print('really want to upload this file? [y/n] ')
      reply = input().lower().strip()
      if reply not in ('y', 'yes'):
        exit(1)

    print('Registry "{}" ({})'.format(registry.name, registry.base_url))
    if not registry.username:
      registry.username = input('Username? ')
    else:
      print('Username?', registry.username)
    if not registry.password:
      registry.password = getpass.getpass('Password? ')

    if dry:
      print('Not actually uploading things... (dry mode)')
    else:
      msg = registry.upload(self.manifest['name'], self.manifest['version'], filename, force)
      print(msg)

  def publish(self, user, password, force, dry, registry):
    if not self.manifest.get('publish', True):
      print('Error: publish field is False, the package can not be published.')
      exit(1)
    self.run('pre-publish', [], script_only=True)
    filename = self.dist()
    print('Uploading "{}" ...'.format(filename))
    self.upload(filename, user, password, force, dry, registry)
    self.run('post-publish', [], script_only=True)

  def run(self, script, args, script_only=False, directory=None, globals=None):
    bindir = find_nearest_bin_directory(pathlib.Path.cwd())
    if not bindir:
      bindir = env.get_directories('local')['bin']
    oldpath = os.environ.get('PATH', '')
    os.environ['PATH'] = str(bindir) + os.pathsep + oldpath
    try:
      if (not self.manifest or script not in self.manifest.get('scripts', {})) and not script_only:
        self._run_command(shlex_quote(script) + ' ' + ' '.join(map(shlex_quote, args)))
      else:
        self._run_script(script, args, directory=directory, globals=globals)
    finally:
      os.environ['PATH'] = oldpath
    return True

  def _run_script(self, script, args, directory=None, globals=None):
    """
    Invoke a script for the specified *event* name. Does nothing if no script
    for the specified event is specified.
    """

    if script not in self.manifest.get('scripts', {}):
      return

    args = list(args)
    if script != 'pre-script':
      self._run_script('pre-script', [script] + args)

    request = self.manifest.get('scripts', {})[script].strip()
    if request.startswith('$'):
      return self._run_command(request[1:].strip())
    else:
      args = shlex.split(request) + args
      require = context.require
      request = args.pop(0)
      request = os.path.abspath(os.path.join(directory or self.manifest.directory, request))
      module = require.resolve(request)
      module.init()
      vars(module.namespace).update(globals or {})
      with require.context.push_main(module):
        require.context.load_module(module, do_init=False)

  def _run_command(self, command):
    # TODO: On Windows, fall back to CMD.exe if SHELL is not defined.
    command = [os.environ['SHELL'], '-c', command]
    print('$', ' '.join(shlex_quote(x) for x in command))
    try:
      return subprocess.call(command)
    except (OSError, IOError) as exc:
      print('Error: can not run "{}" ({})'.format(cmd, exc))
      return getattr(exc, 'errno', 127)
