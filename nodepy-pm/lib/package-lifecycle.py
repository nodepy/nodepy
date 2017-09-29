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

import getpass
import nodepy
import os
import shlex
import subprocess
import tarfile

from six.moves import input
from sys import exit

try:
  from shlex import quote as shlex_quote
except ImportError:
  from pipes import quote as shlex_quote

import config from './config'
import logger from './logger'
import _install from './install'
import _manifest from './manifest'
import {RegistryClient, get_package_archive_name} from './registry'


class PackageLifecycle(object):

  @staticmethod
  def find_package_json(path):
    """
    Finds the first `package.json` file in *path* or any of its parent
    directories and returns it. Returns #None if no file can be found.
    """

    for directory in nodepy.upiter_directory(path):
      fn = os.path.join(directory, 'package.json')
      if os.path.isfile(fn):
        return fn

  def __init__(self, directory='.', dist_dir=None, manifest=None, allow_no_manifest=False):
    if manifest is None:
      if not dist_dir:
        dist_dir = os.path.join(directory, 'dist')
      fn = self.find_package_json(directory)
      if not fn and not allow_no_manifest:
        print('Error: package.json not found')
        exit(1)
      if fn:
        try:
          manifest = _manifest.parse(fn)
        except _manifest.InvalidPackageManifest as e:
          if allow_no_manifest:
            logger.warn('Invalid package manifest (%s): %s', e.filename, str(e.cause).split('\n')[0])
          else:
            raise
    self.manifest = manifest
    self.dist_dir = dist_dir

  def dist(self):
    self.run('pre-dist', [], script_only=True)
    filename = get_package_archive_name(self.manifest.name,
        self.manifest.version)
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
    registry = RegistryClient.get(registry or 'default')
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
        != registry.get_package_archive_name(self.manifest.name, self.manifest.version):
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
      msg = registry.upload(self.manifest.name, self.manifest.version, filename, force)
      print(msg)

  def publish(self, user, password, force, dry, registry):
    if self.manifest.private:
      print('Error: the package is marked as private and can not be published.')
      exit(1)
    self.run('pre-publish', [], script_only=True)
    filename = self.dist()
    print('Uploading "{}" ...'.format(filename))
    self.upload(filename, user, password, force, dry, registry)
    self.run('post-publish', [], script_only=True)

  def run(self, script, args, script_only=False):
    modules_dir = nodepy.find_nearest_modules_directory('.')
    if modules_dir:
      bindir = os.path.join(modules_dir, '.bin')
    else:
      bindir = _install.get_directories('local')['bin']
    oldpath = os.environ.get('PATH', '')
    os.environ['PATH'] = bindir + os.pathsep + oldpath
    try:
      if (not self.manifest or script not in self.manifest.scripts) and not script_only:
        self._run_command(shlex_quote(script) + ' ' + ' '.join(map(shlex_quote, args)))
      else:
        self._run_script(script, args=args)
    finally:
      os.environ['PATH'] = oldpath
    return True

  def _run_script(self, script, args):
    """
    Invoke a script for the specified *event* name. Does nothing if no script
    for the specified event is specified.
    """

    if script not in self.manifest.scripts:
      return

    args = list(args)
    if script != 'pre-script':
      self._run_script('pre-script', [script] + args)

    request = self.manifest.scripts[script].strip()
    if request.startswith('!'):
      return self._run_command(request[1:])
    else:
      args = shlex.split(request) + args
      return nodepy.main(['--current-dir', self.manifest.directory] + args)

  def _run_command(self, command):
    # TODO: On Windows, fall back to CMD.exe if SHELL is not defined.
    command = [os.environ['SHELL'], '-c', command]
    try:
      return subprocess.call(command)
    except (OSError, IOError) as exc:
      print('Error: can not run "{}" ({})'.format(cmd, exc))
      return getattr(exc, 'errno', 127)


module.exports = PackageLifecycle
