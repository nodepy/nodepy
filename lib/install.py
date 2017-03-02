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

__all__ = ['InstallError', 'Installer', 'walk_package_files']

import os
import nodepy
import pip.commands
import shlex
import shutil
import six
import sys
import tarfile
import tempfile
import traceback

from fnmatch import fnmatch

_registry = require('./registry')
_config = require('./config')
_download = require('./util/download')
_script = require('./util/script')
refstring = require('./refstring')

parse_manifest = require('./manifest').parse
PackageManifest = require('./manifest').PackageManifest
InvalidPackageManifest = require('./manifest').InvalidPackageManifest

PACKAGE_LINK = '.nodepy-link'
PPYM_INSTALLED_FILES = '.ppym-installed-files'


default_exclude_patterns = [
    '.DS_Store', '.svn/*', '.git', '.git/*', 'nodepy_modules/*',
    '*.pyc', '*.pyo', 'dist/*']


def _makedirs(path):
  if not os.path.isdir(path):
    os.makedirs(path)


def _match_any_pattern(filename, patterns):
  return any(fnmatch(filename, x) for x in patterns)


def _check_include_file(filename, include_patterns, exclude_patterns):
  if _match_any_pattern(filename, exclude_patterns):
    return False
  if not include_patterns:
    return True
  return _match_any_pattern(filename, include_patterns)


def is_virtualenv():
  return hasattr(sys, 'real_prefix') or (sys.prefix == sys.base_prefix)


class PackageNotFound(Exception):
  pass


def walk_package_files(manifest):
  """
  Walks over the files included in a package and yields (abspath, relpath).
  """

  inpat = manifest.dist.get('include_files', [])
  expat = manifest.dist.get('include_files', []) + default_exclude_patterns

  for root, __, files in os.walk(manifest.directory):
    for filename in files:
      filename = os.path.join(root, filename)
      rel = os.path.relpath(filename, manifest.directory)
      if rel == 'package.json' or _check_include_file(rel, inpat, expat):
        yield (filename, rel)


class Installer:
  """
  This class manages the installation/uninstallation procedure.
  """

  def __init__(self, registry=None, upgrade=False, global_=False, strict=False):
    self.reg = registry or _registry.RegistryClient(_config['registry'])
    self.upgrade = upgrade
    self.global_ = global_
    self.strict = strict
    if self.global_:
      if is_virtualenv():
        self.dirs = {
          'packages': os.path.join(sys.prefix, 'share', 'nodepy_modules'),
          'bin': os.path.join(sys.prefix, 'Scripts' if os.name == 'nt' else 'bin'),
          'python_modules': os.path.join(sys.prefix, 'share', 'nodepy_modules', '.pymodules'),
          'reference_dir': six.text_type(os.path.join(sys.prefix, 'share'))
        }
      else:
        self.dirs = {
          'packages': os.path.join(_config['prefix'], 'nodepy_modules'),
          'bin': os.path.join(_config['prefix'], 'bin'),
          'python_modules': os.path.join(_config['prefix'], 'nodepy_modules', '.pymodules'),
          'reference_dir': six.text_type(_config['prefix'])
        }
    else:
      self.dirs = {
        'packages': 'nodepy_modules',
        'bin': 'nodepy_modules/.bin',
        'python_modules': 'nodepy_modules/.pymodules',
        'reference_dir': six.text_type(os.getcwd())
      }

  def find_package(self, package):
    """
    Finds an installed package and returns its #PackageManifest.
    Raises #PackageNotFound if the package could not be found, or possibly
    an #InvalidPackageManifest exception if the manifest is invalid.

    If #Installer.strict is set, the package is only looked for in the target
    packages directory instead of all possibly inherited paths.
    """

    refstring.parse_package(package)
    dirname = os.path.join(self.dirs['packages'], package)
    if not os.path.isdir(dirname):
      raise PackageNotFound(package)

    # TODO: Follow package links
    return parse_manifest(os.path.join(dirname, 'package.json'))

  def uninstall(self, package_name):
    """
    Uninstalls a package by name.
    """

    try:
      manifest = self.find_package(package_name)
    except PackageNotFound:
      print('Package "{}" not installed'.format(package_name))
      return False
    else:
      return self.uninstall_directory(manifest.directory)

  def uninstall_directory(self, directory):
    """
    Uninstalls a package from a directory. Returns True on success, False
    on failure.
    """

    link_fn = os.path.join(directory, PACKAGE_LINK)
    if os.path.isfile(link_fn):
      with open(link_fn, 'r') as fp:
        manifest_fn = os.path.join(fp.read().rstrip('\n'), 'package.json')
    else:
      manifest_fn = os.path.join(directory, 'package.json')

    try:
      manifest = parse_manifest(manifest_fn)
    except InvalidPackageManifest as exc:
      print('Can not uninstall: directory "{}": Invalid manifest": {}'.format(directory, ext))
      return False

    print('Uninstalling "{}" from "{}"{}...'.format(manifest.identifier,
        directory, ' before upgrade' if self.upgrade else ''))

    filelist_fn = os.path.join(directory, PPYM_INSTALLED_FILES)
    installed_files = []
    if not os.path.isfile(filelist_fn):
      print('  Warning: No `{}` found in package directory'.format(PPYM_INSTALLED_FILES))
    else:
      with open(filelist_fn, 'r') as fp:
        for line in fp:
          installed_files.append(line.rstrip('\n'))

    for fn in installed_files:
      try:
        os.remove(fn)
        print('  Removed "{}"...'.format(fn))
      except OSError as exc:
        print('  "{}":'.format(fn), exc)
    shutil.rmtree(directory)
    return True

  def install_dependencies_for(self, manifest):
    """
    Installs the Node.py and Python dependencies of a #PackageManifest.
    """

    if manifest.dependencies:
      print('Installing dependencies for "{}"...'.format(manifest.identifier))
      if not self.install_dependencies(manifest.dependencies):
        return False
    if manifest.python_dependencies:
      print('Installing Python dependencies for "{}"...'.format(manifest.identifier))
      if not self.install_python_dependencies(manifest.python_dependencies):
        return False

    return True

  def install_dependencies(self, deps):
    """
    Install all dependencies specified in the dictionary *deps*.
    """

    install_deps = []
    for name, version in deps.items():
      try:
        dep = self.find_package(name)
      except PackageNotFound as exc:
        install_deps.append((name, version))
      else:
        if not version(dep.version):
          print('  Warning: Dependency "{}@{}" unsatisfied, have "{}" installed'
              .format(name, version, dep.identifier))
        else:
          print('  Skipping satisfied dependency "{}@{}", have "{} installed'.
              format(name, version, dep.identifier))

    if not install_deps:
      return True

    depfmt = ', '.join(refstring.join(n, version=v) for (n, v) in install_deps)
    print('  Installing dependencies:', depfmt)
    for name, version in install_deps:
      if not self.install_from_registry(name, version):
        return False

    return True

  def install_python_dependencies(self, deps):
    """
    Install all Python dependencies specified in *deps* using Pip.
    """

    install_modules = []
    for name, version in deps.items():
      install_modules.append(name + version)

    # TODO: Upgrade strategy?
    # TODO: Skip modules we have already installed? (Pip will show a big info message)
    # TODO: This install method always behaves like `strict`, ALL modules
    #       will be installed into the target directory if they are not already
    #       in the directory. In reality when using Node.py, we take .pymodule
    #       directories of a lot of paths into account.

    if install_modules:
      print('  Installing Python dependencies via Pip:', ' '.join(install_modules))
      cmd = ['--target', self.dirs['python_modules']] + install_modules
      res = pip.commands.install.InstallCommand().main(cmd)
      if res != 0:
        print('Error: `pip install` failed with exit-code', res)
        return False

    return True

  def install_from_directory(self, directory, develop=False, expect=None):
    """
    Installs a package from a directory. The directory must have a
    `package.json` file. If *expect* is specified, it must be a tuple of
    (package_name, version) that is expected to be installed with *directory*.
    The argument is used by #install_from_registry().

    Returns True on success, False on failure.
    """

    filename = os.path.normpath(os.path.abspath(os.path.join(directory, 'package.json')))

    try:
      manifest = parse_manifest(filename)
    except FileNotFoundError:
      print('Error: directory "{}" contains no package manifest'.format(directory))
      return False
    except InvalidPackageManifest as exc:
      print('Error: directory "{}":'.format(directory), exc)
      return False

    if expect is not None and (manifest.name, manifest.version) != expect:
      print('Error: Expected to install "{}@{}" but got "{}" in "{}"'
          .format(expect[0], expect[1], manifest.identifier, directory))
      return False

    print('Installing "{}"...'.format(manifest.identifier))
    target_dir = os.path.join(self.dirs['packages'], manifest.name)

    # Error if the target directory already exists. The package must be
    # uninstalled before it can be installed again.
    if os.path.exists(target_dir):
      if not self.upgrade:
        print('  Note: install directory "{}" already exists, specify --upgrade'.format(target_dir))
        return True
      if not self.uninstall_directory(target_dir):
        return False

    # Install dependencies.
    if not self.install_dependencies_for(manifest):
      return False

    installed_files = []

    print('Installing "{}" to "{}" ...'.format(manifest.identifier, target_dir))
    _makedirs(target_dir)
    if develop:
      # Create a link file that contains the path to the actual package directory.
      print('  Creating {} to "{}"...'.format(PACKAGE_LINK, directory))
      linkfn = os.path.join(target_dir, PACKAGE_LINK)
      with open(linkfn, 'w') as fp:
        fp.write(os.path.abspath(directory))
      installed_files.append(linkfn)
    else:
      for src, rel in walk_package_files(manifest):
        dst = os.path.join(target_dir, rel)
        _makedirs(os.path.dirname(dst))
        print('  Copying', rel, '...')
        shutil.copyfile(src, dst)
        installed_files.append(dst)

    # Create scripts for the 'scripts' and 'bin' fields in the package manifest.
    for script_name, command in manifest.script.items():
      print('  Installing script "{}"...'.format(script_name))
      installed_files += _script.make_command_script(
          script_name, self.dirs['bin'], shlex.split(command))
    for script_name, filename in manifest.bin.items():
      print('  Installing script "{}"...'.format(script_name))
      filename = os.path.abspath(os.path.join(target_dir, filename))
      installed_files += _script.make_nodepy_script(
          script_name, self.dirs['bin'], filename, self.dirs['reference_dir'])

    # Write down the names of the installed files.
    with open(os.path.join(target_dir, PPYM_INSTALLED_FILES), 'w') as fp:
      for fn in installed_files:
        fp.write(fn)
        fp.write('\n')

    if manifest.postinstall:
      print('  Running postinstall script "{}"...'.format(manifest.postinstall))
      filename = os.path.join(target_dir, manifest.postinstall)
      try:
        nodepy.main([filename], standalone_mode=False)
      except BaseException as exc:
        print('  Error in postinstall script "{}"'.format(filename))
        traceback.print_exc()
        return False

    return True

  def install_from_archive(self, archive, expect=None):
    """
    Install a package from an archive.
    """

    directory = tempfile.mkdtemp(suffix='_' + os.path.basename(archive) + '_unpacked')
    print('Unpacking "{}"...'.format(archive))
    try:
      with tarfile.open(archive) as tar:
        tar.extractall(directory)
      return self.install_from_directory(directory, expect=expect)
    finally:
      shutil.rmtree(directory)

  def install_from_registry(self, package_name, selector):
    """
    Install a package from a registry.
    """

    # Check if the package already exists.
    try:
      package = self.find_package(package_name)
    except PackageNotFound:
      pass
    else:
      if not selector(package.version):
        print('  Warning: Dependency "{}@{}" unsatisfied, have "{}" installed'
            .format(package_name, selector, package.identifier))
      if not self.upgrade:
        print('package "{}@{}" already installed, specify --upgrade'.format(
            package.name, package.version))
        return True

    print('Finding package matching "{}@{}"...'.format(package_name, selector))
    info = self.reg.find_package(package_name, selector)
    assert info.name == package_name, info

    print('Downloading "{}@{}"...'.format(info.name, info.version))
    response = self.reg.download(info.name, info.version)
    filename = _download.get_response_filename(response)

    tmp = None
    try:
      with tempfile.NamedTemporaryFile(suffix='_' + filename, delete=False) as tmp:
        progress = _download.DownloadProgress(30, prefix='  ')
        _download.download_to_fileobj(response, tmp, progress=progress)
      return self.install_from_archive(tmp.name, expect=(package_name, info.version))
    finally:
      if tmp and os.path.isfile(tmp.name):
        os.remove(tmp.name)


class InstallError(Exception):
  pass
