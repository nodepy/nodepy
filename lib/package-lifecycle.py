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

config = require('./config')
_install = require('./install')
_manifest = require('./manifest')
registry = require('./registry')


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

  def __init__(self, directory='.', dist_dir=None, manifest=None):
    if manifest is None:
      if not dist_dir:
        dist_dir = os.path.join(directory, 'dist')
      fn = self.find_package_json(directory)
      if not fn:
        print('Error: package.json not found')
        exit(1)
      manifest = _manifest.parse(fn)
    self.manifest = manifest
    self.dist_dir = dist_dir

  def dist(self):
    self.run('pre-dist', [])
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
    self.run('post-dist', [])
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
    if self.manifest.private:
      print('Error: the package is marked as private and can not be published.')
      exit(1)
    self.run('pre-publish', [])
    filename = self.dist()
    self.upload(filename, user, password, force, dry)
    self.run('post-publish', [])

  def run(self, script, args):
    bindir = nodepy.Directories(self.manifest.directory).bindir
    oldpath = os.environ.get('PATH', '')
    os.environ['PATH'] = bindir + os.pathsep + oldpath
    try:
      if script not in self.manifest.scripts:
        return False
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
    args = shlex.split(self.manifest.scripts[script]) + list(args)
    request = args.pop(0)

    if script != 'pre-script':
      self._run_script('pre-script', [script] + args)

    if request.startswith('!'):
      # Execute as a shell command instead.
      # TODO: On Windows, fall back to CMD.exe if SHELL is not defined.
      cmd = request[1: ] + ' ' + ' '.join(map(shlex_quote, args))
      command = [os.environ['SHELL'], '-c', cmd]
      try:
        return subprocess.call(command)
      except (OSError, IOError):
        print('Error: can not run "{}"'.format(cmd))
        return 1
    else:
      require.exec_main(request, self.directory, argv=args, cache=False)


exports = PackageLifecycle
