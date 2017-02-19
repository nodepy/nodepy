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
"""
cpm -- a Python-ish package manager
===================================

Contents:

- #PackageManifest represents a `cpm.json` manifest in memory
- #Finder finds packages in a directory and yields #PackageManifest#s
- #Package represents a package and its modules
- #Module represents a Python module as part of a #Package
- #Loader loads #Package#s and from #PackageManifest#s
- #Cpm represents the package ecosystem and provides the `require()` function
"""

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.1'
__license__ = 'MIT'

import collections
import json
import jsonschema
import os
import posixpath
import shutil
import textwrap
import types

from .core import Loader, Finder, DefaultFinder, Module, PackageManifest
from .exceptions import *
from .utils import pathutils, refstring, semver
from distlib.scripts import ScriptMaker
from fnmatch import fnmatch


class Cpm:
  """
  This class manages the CPM environment and the default #Loader configuration.
  """

  def __init__(self, prefix='~/.cpm', local_modules_dir='cpm_modules'):
    self.prefix = os.path.expanduser(prefix)
    self.local_modules_dir = local_modules_dir
    self.loader = Loader()
    self.local_finder = DefaultFinder(local_modules_dir)
    self.global_finder = DefaultFinder(os.path.join(self.prefix, 'modules'))
    self.main_package = None
    self.allow_unknown_dependencies = True

  @property
  def finders(self):
    return (self.local_finder, self.global_finder)

  def update_cache(self):
    errors = []
    for finder in self.finders:
      errors += finder.update_cache()
    return errors

  def load_main_package(self):
    """
    Loads and returns the main package from the current directory. Can raise
    any exception raised by #Loader.load_package_manifest().
    """

    if self.main_package:
      return self.main_package
    manifest = self.local_finder.load_package_manifest('.')
    package = self.loader.load_package(manifest)
    return package

  def load_package(self, package_name, selector):
    """
    Uses the #finder to find the best possible match for *package_name*
    and returns a #Package object. If no matching package could be found,
    #PackageNotFound is raised.

    If a package with the specified *package_name* is already loaded but
    does not match the specified version *selector*, a
    #PackageMultiplicityNotAllowed exception is raised unless
    #allow_multiple_versions is enabled.
    """

    if not package_name:
      raise ValueError('empty package_name')
    if not selector:
      selector = semver.Selector('*')

    # Re-use a matching already loaded package.
    packages = self.loader.get_packages(package_name, selector)
    if packages:
      return packages[0]

    # Find all available choices.
    manifest = None
    for finder in self.finders:
      choices = list(finder.find_packages(package_name, selector))
      if choices:
        manifest = selector.best_of(choices, key=lambda x: x.version)
        break
    else:
      raise PackageNotFound(package_name, selector)

    # And get the best match.
    manifest = selector.best_of(choices, key=lambda x: x.version)
    assert manifest.name == package_name
    return self.loader.load_package(manifest)  # Can raise DuplicatePackage

  def require(self, name, origin):
    """
    This method is a combination of #load_package(), #Package.load_module()
    and #exec_module(). Given a package *name* and optionally the submodule
    name encoded in the same string, it will load the #Package and module
    and execute it (if it is not already executed). If *name* begins with a
    curdir (`./`) or pardir (`../`), a module is loaded from the currently
    executed package instead.

    This method can only be used from inside the execution of another #Module
    which must be specified with the *origin* parameter.

    If the requested package is not listed as a dependency of the *origin*
    #Module#s #Package#s dependencies, an #UnknownDependency exception is
    raised.
    """

    if not isinstance(name, str):
      raise TypeError('name must be a string')
    if not isinstance(origin, Module):
      raise TypeError('origin must be a cpm.Module')

    if name.startswith('./') or name.startswith('../'):
      package = origin.package
      module = posixpath.join(posixpath.dirname(origin.name), name)
      module = posixpath.normpath(module)
    else:
      package_name, module = name.partition('/')[::2]
      selector = origin.package.manifest.dependencies.get(package_name)
      if not self.allow_unknown_dependencies and selector is None:
        raise UnknownDependency(origin.package, package_name)
      package = self.load_package(package_name, selector)

    module = package.load_module(module or None)
    if not module.executed:
      module.exec_()
    return module

  def get_install_dirs(self, global_):
    if global_:
      return {'modules': os.path.join(self.prefix, 'modules'),
              'bin': os.path.join(self.prefix, 'bin')}
    else:
      return {'modules': self.local_modules_dir,
              'bin': os.path.join(self.local_modules_dir, '.bin')}

  def install_package_from_directory(self, directory, dirs):
    manifest = PackageManifest.parse(directory)
    install_dir = os.path.join(dirs['modules'], manifest.name)
    if os.path.exists(install_dir) :
      raise InstallError('install directory "{}" already exists'.format(install_dir))

    # Install CPM dependencies if they are unmet.
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

    installed_files = []

    # Add default exclude patterns.
    exclude_files = list(manifest.exclude_files)
    exclude_files.append('cpm_modules/*')
    exclude_files.append('.git/*')
    exclude_files.append('.svn/*')
    exclude_files.append('*.pyc')

    # Copy the package files.
    print('Installing "{}" to "{}" ...'.format(manifest.identifier, install_dir))
    pathutils.makedirs(install_dir)
    for root, __, files in os.walk(directory):
      for filename in files:
        filename = os.path.join(root, filename)
        rel = os.path.relpath(filename, directory)
        # Skip the file if any of the skip patterns match.
        if any(fnmatch(rel, pat) for pat in exclude_files):
          continue
        dst = os.path.join(install_dir, rel)
        pathutils.makedirs(os.path.dirname(dst))
        print('  Copying', rel, '...')
        shutil.copyfile(filename, dst)
        installed_files.append(dst)

    # Create scripts.
    for script_name, ref in manifest.scripts.items():
      try:
        ref = refstring.parse(ref)
      except ValueError as exc:
        raise InstallError('invalid script "{}": {}'.format(script_name, exc))
      if not ref.package:
        ref = refstring.Ref(manifest.name, manifest.version, ref.module, ref.member)
      print('  Installing script "{}"...'.format(script_name))
      maker = ScriptMaker(None, dirs['bin'])
      maker.clobber = True
      maker.variants = set(('',))
      maker.set_mode = True
      # TODO: The script must support being called from any CWD.
      maker.script_template = textwrap.dedent('''
        import sys, cpm.main
        if __name__ == '__main__':
          sys.argv = [sys.argv[0], 'run', {!r}] + sys.argv[1:]
          cpm.main.cli()
        '''.format(refstring.join(*ref)))
      installed_files += maker.make(script_name + '=foo')

    # TODO Install Python dependencies.

    with open(os.path.join(install_dir, '.installed-files'), 'w') as fp:
      for filename in installed_files:
        fp.write(filename)
        fp.write('\n')

  def install_package(self, package_name, selector):
    """
    Install packages from a remote registry.

    TODO
    """

    raise InstallError('installation from registry not implement')


class AddVars:
  """
  Objects of this class can be added to #Loader.before_exec to initialize
  #Module#s with a default namespace before they are executed.
  """

  def __init__(self, vars=None):
    self.vars = {} if vars is None else vars

  def __call__(self, module):
    vars(module.namespace).update(self.vars)


class AddRequire:
  """
  Adds the default `require()` method to the namespace of a #Module before it
  is executed. An instance of this class must be added to #Loader.before_exec.
  Note that the *loader* argument must match the #Loader that this object is
  added to.
  """

  def __init__(self, cpm):
    self.cpm = cpm

  def __call__(self, module):
    module.namespace.require = Require(self.cpm)


class Require:
  """
  Helper class that implements the `require()` function. Use #AddRequire()
  in #Loader.before_exec to add an instance of this class to loaded module's
  namespaces.
  """

  def __init__(self, cpm):
    self.cpm = cpm

  def __call__(self, name):
    module = self.cpm.require(name, self.cpm.loader.get_current_module())
    return module.namespace
