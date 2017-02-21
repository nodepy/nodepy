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

__all__ = ['Module', 'Package', 'MainPackage', 'PackageContainer', 'NoSuchModule']

import os
import types
from ..utils import semver


class Module:
  """
  This class represents an actual Python file that can be executed directly
  via **upython** or be `require()`d by another module. A module may not be part
  of a #Package if it is executed directly (depending on whether the package
  can be resolved from the module's location).
  """

  def __init__(self, package, filename):
    self.package = package
    self.filename = filename
    self.executed = False
    self.namespace = types.ModuleType(self.identifier)
    self.namespace.__name__ = self.name
    self.namespace.__file__ = filename

  def __repr__(self):
    exec_info = '' if self.executed else ' (not executed)'
    return '<Module "{}" from "{}"{}>'.format(
        self.identifier, self.filename, exec_info)

  @property
  def name(self):
    if not self.package:
      return '__main__'
    name = self.filename[:-3] if self.filename.endswith('.py') else self.filename
    name = os.path.relpath(name, self.package.directory)
    return name.replace(os.sep, '/')

  @property
  def identifier(self):
    if not self.package:
      return '/__main__'
    return '{}/{}'.format(self.package.identifier, self.name)


class Package:
  """
  This class represents a package and provides access to its submodules.
  """

  def __init__(self, manifest, module_class=Module):
    self.manifest = manifest
    self.module_class = module_class
    self.modules = {}
    self.extra_module_files = {}
    self.private_packages = PackageContainer(Package, module_class)

  def __repr__(self):
    return '<{} "{}" from "{}">'.format(type(self).__name__, self.identifier, self.directory)

  @property
  def name(self):
    return self.manifest.name

  @property
  def version(self):
    return self.manifest.version

  @property
  def identifier(self):
    return self.manifest.identifier

  @property
  def directory(self):
    return self.manifest.directory

  def load_module_from_filename(self, filename):
    """
    Loads a module from a filename. The `.py` suffix can be skipped for
    *filename*, but the actual file that will be loaded must have a `.py`
    suffix.
    """

    if os.path.isabs(filename):
      rel = os.path.relpath(filename, self.directory)
    else:
      rel = filename

    if rel == os.curdir:
      rel = self.manifest.main
    elif rel.startswith(os.pardir):
      raise ValueError('"{}" not part of this package'.format(filename))

    rel = rel.replace(os.sep, '/')
    if rel.endswith('.py'):
      return self.load_module(rel[:-3])
    else:
      if rel in self.extra_module_files:
        return self.extra_module_files[rel]
      module = self.module_class(self, filename)
      self.extra_module_files[rel] = module
      return module

  def load_module(self, name=None):
    """
    Returns a #Module instance from the specified module *name*. If #None is
    passed, the package's main module will be loaded.

    # Raises
    NoSuchModule
    """

    if name is None:
      name = self.manifest.main
    if name in self.modules:
      return self.modules[name]

    filename = os.path.join(self.directory, name + '.py')
    filename = os.path.normpath(os.path.abspath(filename))
    if not os.path.isfile(filename):
      raise NoSuchModule(self, name)

    module = self.module_class(self, filename)
    self.modules[name] = module
    return module


class MainPackage(Package):
  """
  This #Package subclass is used when executing scripts directly that are not
  part of a #Package with a `package.json` manifest.
  """

  def __init__(self, module_class=Module):
    super().__init__(None, module_class)
    self._directory = os.getcwd()

  @property
  def name(self):
    return '__main__'

  @property
  def version(self):
    return semver.Version('1.0.0')

  @property
  def identifier(self):
    return '{}@{}'.format(self.name, self.version)

  @property
  def directory(self):
    return self._directory


class PackageContainer:
  """
  A container for keep track of loaded packages. There is a global package
  container in every #Session, but a single #Package also have a package
  container for private packages (ones that are not in the global and local
  package directory).
  """

  def __init__(self, package_class=Package, module_class=Module):
    self._packages = {}
    self._package_class = package_class
    self._module_class = module_class

  def __repr__(self):
    return repr(self._packages)

  def __getitem__(self, name):
    return self._packages[name]

  def __setitem__(self, name, value):
    self._packages[name] = value

  def __contains__(self, name):
    return name in self._packages

  def get(self, *args):
    return self._packages.get(*args)

  def add_package(self, manifest, return_existing=False):
    """
    Adds a #Package to directly to the container from a #PackageManifest.
    """

    if manifest.name in self._packages:
      if not return_existing:
        raise RuntimeError('a package "{}" is already loaded'.format(manifest.name))
      package = self._packages[manifest.name]
      if package.manifest != manifest:
        raise RuntimeError('requested to return existing package for '
            'manifest {!r} but the existing package\'s manifest doesn\'t '
            'match'.format(manifest))
      return package

    package = self._package_class(manifest, self._module_class)
    assert isinstance(package, Package)
    self._packages[manifest.name] = package
    return package


class NoSuchModule(Exception):
  """
  This exception is raised in #Package.load_module() if the requested module
  does not exist.
  """

  def __init__(self, package, module_name):
    self.package = package
    self.module_name = module_name

  def __str__(self):
    return 'No module "{}" in "{}"'.format(
        self.module_name, self.package.identifier)
