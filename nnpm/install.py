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

__all__ = ['InstallError', 'install_from_directory', 'install_from_registry']

import os
import shlex
import shutil
from distlib.scripts import ScriptMaker
from fnmatch import fnmatch
from nnp.core.manifest import PackageManifest


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
  code = 'import sys, nnp.main;nnp.main.run(%r, local_dir=%r)' % (filename, local_dir)
  return _make_python_script(script_name, code, directory)


def install_from_directory(source_directory, dirs):
  """
  Install an nnp package from a directory. The directory must provide a
  `package.json` file. An #InstallError is raised when the installation of the
  package or any of its dependencies fail.

  *dirs* must be a dictionary that provides information on the directories
  of where to install which parts of the package. The keys it must provide
  are `'bin'` and `'packages`', `'python_modules'` and `'local_dir'`.
  """

  manifest = PackageManifest.parse(source_directory)
  target_dir = os.path.join(dirs['packages'], manifest.name)
  print(target_dir)

  # Error if the target directory already exists. The package must be
  # uninstalled before it can be installed again.
  if os.path.exists(target_dir) :
    raise InstallError('install directory "{}" already exists'.format(target_dir))

  # TODO: Install nnp packages that are not already installed.
  print('warning: installation of nnp dependencies not implemented')
  """
  if manifest.dependencies:
    print('Collecting dependencies for "{}"...'.format(manifest.identifier))
  deps = []
  for dep_name, dep_sel in manifest.dependencies.items():
    try:
      self.load_package(dep_name, dep_sel)
    except PackageNotFound as exc:
      deps.append((dep_name, dep_sel))
    else:
      print('  Skipping satisfied dependency "{}"'.format(
          refstring.join(dep_name, dep_sel)))
  if deps:
    print('Installing dependencies:', ', '.join(refstring.join(*d) for d in deps))
    for dep_name, dep_sel in deps:
      self.install_package(dep_name, dep_sel)
  """

  # TODO: Install python dependencies.
  print('warning: installation of python dependencies not implemented.')

  installed_files = []

  print('Installing "{}" to "{}" ...'.format(manifest.identifier, target_dir))
  include_files = list(manifest.dist.get('include_files', []))
  exclude_files = list(manifest.dist.get('exclude_files', []))
  _makedirs(target_dir)

  if not include_files and not exclude_files:
    print('  Warning: no include_files and no exclude_files specified, the '
        'whole package directory will be installed')

  # Add default exclude patterns.
  exclude_files.append('.DS_Store')
  exclude_files.append('.svn/*')
  exclude_files.append('.git/*')
  exclude_files.append('nnp_packages/*')
  exclude_files.append('*.pyc')
  exclude_files.append('*.pyo')

  for root, __, files in os.walk(source_directory):
    for filename in files:
      filename = os.path.join(root, filename)
      rel = os.path.relpath(filename, source_directory)
      if rel != 'package.json' and not _check_include_file(rel, include_files, exclude_files):
          continue

      dst = os.path.join(target_dir, rel)
      _makedirs(os.path.dirname(dst))
      print('  Copying', rel, '...')
      shutil.copyfile(filename, dst)
      installed_files.append(dst)

  # Create scripts for the 'scripts' and 'bin' fields in the package manifest.
  for script_name, command in manifest.scripts.items():
    print('  Installing script "{}"...'.format(script_name))
    installed_files += _make_script(script_name, shlex.split(command), dirs['bin'])
  for script_name, filename in manifest.bin.items():
    print('  Installing script "{}"...'.format(script_name))
    filename = os.path.abspath(os.path.join(target_dir, filename))
    installed_files += _make_bin(script_name, filename, dirs['local_dir'], dirs['bin'])


def install_from_registry(self, package_name, selector):
  """
  Install packages from a remote registry.

  TODO
  """

  raise InstallError('installation from registry not implement')


class InstallError(Exception):
  pass
