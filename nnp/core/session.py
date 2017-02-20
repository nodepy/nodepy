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
from .executor import *
from .finder import *
from .manifest import *
from .package import *
from ..utils import semver


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
  This class implements the hypervisor and default environment for **nnp**
  packages, handling the loading and module namespace default initialization.
  It provides the #require() function to modules.

  # Parameters
  path (list of str): A list of directories to search for packages in.
  prefix (str): If *path* is not specified, this is the path to the global
    configuration and packages dir. Defaults to `~/.nnp`.
  local_packages (str): If *path* is not specified, this is the path where the
    local packages are located. Defaults to `nnp_packages`.

  # Members

  finders (list of Finder): A list of finders that are employed to find
    packages in the session.
  packages (dict of (str, Package)): A dictionary that maps already loaded
    package names to the actual #Package objects.
  """

  def __init__(self, path=None, prefix=None, local_packages=None,
      package_class=Package, module_class=Module, require_factory=Require):

    if path is None:
      prefix = prefix or os.path.expanduser('~/.nnp')
      path = [local_packages, os.path.join(prefix, 'packages')]

    self.finders = [StandardFinder(x) for x in path]
    self.packages = {}
    self.executor = Executor([self.on_init_module])
    self.package_class = package_class
    self.module_class = module_class
    self.require_factory = require_factory

  @property
  def module(self):
    return self.executor.current_module

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

  def add_package(self, manifest):
    """
    Adds a #Package to directly to the #Session from a #PackageManifest.
    """

    if manifest.name in self.packages:
      raise RuntimeError('a package "{}" is already loaded'.format(manifest.name))
    package = self.package_class(manifest, self.module_class)
    assert isinstance(package, Package)
    self.packages[manifest.name] = package
    return package

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
      package = origin.package
      module = posixpath.join(posixpath.dirname(origin.name), name)
      module = posixpath.normpath(module)
    else:
      package_name, module = name.partition('/')[::2]
      self.on_require(origin, package_name)
      selector = None
      if origin and origin.package:
        selector = origin.package.manifest.dependencies.get(package_name)
      package = self.load_package(package_name, selector)

    module = package.load_module(module or None)
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
