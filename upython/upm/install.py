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

__all__ = ['InstallError', 'install_from_archive', 'install_from_directory',
    'install_from_registry', 'walk_package_files']


import upython.main
import os
import pip.commands
import shlex
import shutil
import tarfile
import tempfile

from distlib.scripts import ScriptMaker
from fnmatch import fnmatch
from ..core import PackageManifest, PackageNotFound
from ..utils import download, refstring

default_exclude_patterns = ['.DS_Store', '.svn/*', '.git/*', 'upython_packages/*', '*.pyc', '*.pyo', 'dist/*']


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

def _make_python_script(script_name, code, directory):
  maker = ScriptMaker(None, directory)
  maker.clobber = True
  maker.variants = set(('',))
  maker.set_mode = True
  maker.script_template = code
  return maker.make(script_name + '=isthisreallynecessary')


def _make_script(script_name, args, directory):
  code = 'import subprocess as s, sys;sys.exit(s.call(%r))' % (list(args),)
  return _make_python_script(script_name, code, directory)


def _make_bin(script_name, filename, local_dir, directory):
  # TODO: If local_dir is None here (for global installs), local module's
  # shouldn't even be considered!
  code = 'import sys, upython.main;upython.main.run(%r, local_dir=%r)' % (filename, local_dir)
  return _make_python_script(script_name, code, directory)


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


def install_from_directory(directory, dirs, registry, expect=None):
  """
  Install an upython package from a directory. The directory must provide a
  `package.json` file. An #InstallError is raised when the installation of the
  package or any of its dependencies fail.

  *dirs* must be a dictionary that provides information on the directories
  of where to install which parts of the package. The keys it must provide
  are `'bin'` and `'packages`', `'python_modules'` and `'local_dir'`.
  """

  manifest = PackageManifest.parse(directory)
  if expect is not None and (manifest.name, manifest.version) != expect:
    raise InstallError('expected to install "{}@{}" but got "{}" in '
        '"{}"'.format(expect[0], expect[1], manifest.identifier, directory))

  session = upython.main.make_session(dirs['local_dir'], exclude_local_dir=bool(dirs['local_dir']))
  target_dir = os.path.join(dirs['packages'], manifest.name)

  # Error if the target directory already exists. The package must be
  # uninstalled before it can be installed again.
  if os.path.exists(target_dir) :
    raise InstallError('install directory "{}" already exists'.format(target_dir))

  # Install upython dependencies.
  if manifest.dependencies:
    print('Collecting dependencies for "{}"...'.format(manifest.identifier))
  deps = []
  for dep_name, dep_sel in manifest.dependencies.items():
    try:
      session.load_package(dep_name, dep_sel)
    except PackageNotFound as exc:
      deps.append((dep_name, dep_sel))
    else:
      print('  Skipping satisfied dependency "{}"'.format(
          refstring.join(dep_name, dep_sel)))
  if deps:
    print('Installing dependencies:', ', '.join(refstring.join(*d) for d in deps))
    for dep_name, dep_sel in deps:
      install_from_registry(dep_name, dep_sel, dirs, registry)

  # Install python dependencies.
  py_modules = []
  for dep_name, dep_version in manifest.python_dependencies.items():
    py_modules.append(dep_name + dep_version)
  if py_modules:
    print('Installing Python dependencies via Pip:', ', '.join(py_modules))
    pip.commands.install.InstallCommand().main(['--target', dirs['python_modules']] + py_modules)

  installed_files = []

  print('Installing "{}" to "{}" ...'.format(manifest.identifier, target_dir))
  _makedirs(target_dir)
  for src, rel in walk_package_files(manifest):
    dst = os.path.join(target_dir, rel)
    _makedirs(os.path.dirname(dst))
    print('  Copying', rel, '...')
    shutil.copyfile(src, dst)
    installed_files.append(dst)

  # Create scripts for the 'scripts' and 'bin' fields in the package manifest.
  for script_name, command in manifest.scripts.items():
    print('  Installing script "{}"...'.format(script_name))
    installed_files += _make_script(script_name, shlex.split(command), dirs['bin'])
  for script_name, filename in manifest.bin.items():
    print('  Installing script "{}"...'.format(script_name))
    filename = os.path.abspath(os.path.join(target_dir, filename))
    installed_files += _make_bin(script_name, filename, dirs['local_dir'], dirs['bin'])

  if manifest.postinstall:
    print('  Running postinstall script "{}"...'.format(manifest.postinstall))
    filename = os.path.join(target_dir, manifest.postinstall)
    upython.main.run(filename)


def install_from_archive(archive, dirs, registry, expect=None):
  """
  Install a package from an archive.
  """

  directory = tempfile.mkdtemp(suffix='_' + os.path.basename(archive) + '_unpacked')
  print('Unpacking "{}"...'.format(archive))
  try:
    with tarfile.open(archive) as tar:
      tar.extractall(directory)
    install_from_directory(directory, dirs, registry, expect=expect)
  finally:
    shutil.rmtree(directory)


def install_from_registry(package_name, selector, dirs, registry):
  """
  Install a package from a registry.
  """

  print('Finding package matching "{}@{}"...'.format(package_name, selector))
  info = registry.find_package(package_name, selector)
  assert info.name == package_name, info

  print('Downloading "{}@{}"...'.format(info.name, info.version))
  response = registry.download(info.name, info.version)
  filename = download.get_response_filename(response)

  tmp = None
  try:
    with tempfile.NamedTemporaryFile(suffix='_' + filename, delete=False) as tmp:
      progress = download.DownloadProgress(30, prefix='  ')
      download.download_to_fileobj(response, tmp, progress=progress)
    return install_from_archive(tmp.name, dirs, registry, expect=(package_name, info.version))
  finally:
    if tmp and os.path.isfile(tmp.name):
      os.remove(tmp.name)


class InstallError(Exception):
  pass
