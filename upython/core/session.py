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

__all__ = ['Require', 'Session', 'DependencyMismatch']

import os
import posixpath

from localimport import localimport
from .executor import *
from .finder import *
from .manifest import *
from .package import *
from ..utils import refstring, semver


class Require:
  """
  Wrapper that calls #Session.require() and returns the "exports" member of
  the #Module.namespace if it exists, otherwise just the namespace.
  """

  def __init__(self, session):
    self.session = session

  def __call__(self, name):
    module = self.session.require(name, self.session.module)
    if hasattr(module.namespace, 'exports'):
      return module.namespace.exports
    return module.namespace


class Session:
  """
  This class implements the hypervisor and default environment for **upython**
  packages, handling the loading and module namespace default initialization.
  It provides the #require() function to modules.

  # Parameters
  path (list of str): A list of directories to search for packages in.
  prefix (str): If *path* is not specified, this is the path to the global
    configuration and packages dir. Defaults to `~/.upython`.
  local_packages (str): If *path* is not specified, this is the path where the
    local packages are located. Defaults to `upython_packages`. If local packages
    should be ignored completely, #False can be specified.
  install_python_path (list of str): A list of additional Python search
    directories that are temporarily installed when entering the session
    context.

  # Members

  finders (list of Finder): A list of finders that are employed to find
    packages in the session.
  packages (dict of (str, Package)): A dictionary that maps already loaded
    package names to the actual #Package objects.
  """

  def __init__(self, path=None, prefix=None, local_packages='upython_packages',
      install_python_path=None, package_class=Package, module_class=Module,
      require_factory=Require):

    prefix = prefix or os.path.expanduser('~/.upython')
    if path is None:
      path = [os.path.join(prefix, 'packages')]
      if local_packages is not False:
        path.insert(0, local_packages)
    if install_python_path is None:
      install_python_path = [os.path.join(prefix, 'pymodules')]
      if local_packages is not False:
        install_python_path.insert(0, os.path.join(local_packages, '.pymodules'))

    self.finders = [StandardFinder(x) for x in path]
    self.packages = PackageContainer(package_class, module_class)
    self.packages['__main__'] = MainPackage(module_class)

    self.executor = Executor([self.on_init_module])
    self.install_python_path = install_python_path
    self.importer = localimport(self.install_python_path, parent_dir=os.getcwd())
    self.require_factory = require_factory

  def __enter__(self):
    self.importer.__enter__()
    return self

  def __exit__(self, *args):
    self.importer.__exit__(*args)

  @property
  def module(self):
    return self.executor.current_module

  def load_module_from_filename(self, filename, parent_package=None):
    """
    Finds the package owning the specified *filename*. If there is no parent
    package directory for the file, a #MainPackage will be created instead (or
    re-used if it already exists) and the file is loaded into that package.

    Returns a #Module object.
    """

    filename = os.path.abspath(filename)
    directory = PackageManifest.find_module_package_directory(filename)

    # Check if the directory is already cached in any of the finders.
    manifest = None
    if directory:
      for finder in self.finders:
        manifest = finder.get_manifest_cache(directory)
        if manifest:
          break

    # If we found a manifest in the finders, it is a package that we would
    # normally be able to find, too. Load it globally.
    if manifest:
      package = self.add_package(manifest, return_existing=True)
    else:
      if directory:
        if not parent_package:
          raise RuntimeError('private packages can only be loaded from an '
              'existing package context')
        manifest = PackageManifest.parse(directory)
        package = parent_package.private_packages.add_package(manifest, True)
      else:
        package = self.packages['__main__']

    return package.load_module_from_filename(filename)

  def on_init_module(self, module):
    """
    Called automatically before a #Module is executed.
    """

    module.namespace.require = self.require_factory(self)

  def on_require(self, origin, package_name):
    """
    This method is called when #require() is called. Can be used to validate
    package dependencies. The default implementation does nothing. The method
    is not called when a local module is loaded.
    """

    pass

  def add_package(self, manifest, return_existing=False):
    """
    Adds a #Package to directly to the #Session from a #PackageManifest.
    """

    return self.packages.add_package(manifest, return_existing)

  def load_package(self, package_name, selector):
    """
    Loads a #Package and returns it. No module is executed at that point.
    """

    if not selector:
      selector = semver.Selector('*')

    if package_name in self.packages:
      package = self.packages[package_name]
      if selector and not selector(package.version):
        raise DependencyMismatch(package, selector)
      return package

    for finder in self.finders:
      try:
        manifest = finder.find_package(package_name, selector)
      except PackageNotFound:
        pass
      else:
        break
    else:
      raise PackageNotFound(package_name, selector)

    return self.add_package(manifest)

  def require(self, name, origin=None, exec_=True):
    """
    This method is a combination of #load_package(), #Package.load_module()
    and #Executor.exec_module(). Given a package *name* and optionally the
    submodule name encoded in the same string, it will load the #Package and
    module and execute it (if it is not already executed). If *name* begins
    with a curdir (`./`) or pardir (`../`), a module is loaded from the
    currently executed package instead.

    Note that the curdir and pardir semantics can only be used when *origin*
    is specified (and is a #Module instance).
    """

    if not isinstance(name, str):
      raise TypeError('name must be a string')
    if origin is not None and not isinstance(origin, Module):
      raise TypeError('origin must be a cpm.Module')

    if name.startswith('./') or name.startswith('../'):
      if not origin or not origin.package:
        raise ValueError('can not use relative require() outside of a package')
      package = origin.package
      filename = posixpath.join(posixpath.dirname(origin.name), name)
      filename = posixpath.join(package.directory, posixpath.normpath(filename))
      if not filename.endswith('.py') and not os.path.exists(filename):
        filename += '.py'
      module = self.load_module_from_filename(filename, package)
    else:
      ref = refstring.parse(name)
      if ref.version or ref.member:
        raise ValueError('invalid refstring for require(): {!r}'.format(name))

      self.on_require(origin, ref.package)
      selector = None
      if origin and origin.package and origin.package.manifest:
        selector = origin.package.manifest.dependencies.get(ref.package)
      package = self.load_package(ref.package, selector)
      module = package.load_module(ref.module or None)

    if not module.executed and exec_:
      self.exec_module(module)
    return module

  def exec_module(self, module):
    return self.executor.exec_module(module)


class DependencyMismatch(Exception):

  def __init__(self, have_package, expected):
    self.have_package = have_package
    self.expected = expected

  def __str__(self):
    return '"{}" already loaded buy required "{}"'.format(
        self.package.identifier, self.expected)
