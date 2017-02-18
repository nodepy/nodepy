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
"""

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.1'
__license__ = 'MIT'

import collections
import json
import jsonschema
import os
import posixpath
import types

from .utils import semver


class NotAPackageDirectory(Exception):
  """
  Raised by #PackageManifest.parse() when the specified directory is not a
  valid package directory (that is, if it does not contain a `cpm.json` file).
  """

  def __init__(self, directory):
    self.directory = directory

  def __str__(self):
    return 'Not a package directory: "{}"'.format(self.directory)


class InvalidPackageManifest(Exception):
  """
  Raised by #PackageManifest.parse() when the package manifest is invalid JSON
  or contains invalid values.
  """

  def __init__(self, filename, cause):
    self.filename = filename
    self.cause = cause

  def __str__(self):
    return 'In file "{}": {}'.format(self.filename, self.cause)


class NoSuchModule(Exception):
  """
  This exception is raised in #Package.get_module() if the requested module
  does not exist. If the #module_name attribute is #None, it represents the
  main package module.
  """

  def __init__(self, package, module_name):
    self.package = package
    self.module_name = module_name

  def __str__(self):
    return 'No module "{}" in "{}"'.format(self.module_name,
        self.package.identifier)


class PackageNotFound(Exception):
  """
  This exception is raised if a package that matches the criteria specified
  with #Loader.load_package() can not be found.
  """

  def __init__(self, package_name, selector):
    self.package_name = package_name
    self.selector = selector or semver.Selector('*')

  def __str__(self):
    return '{}@{}'.format(self.package_name, self.selector)


class PackageMultiplicityNotAllowed(Exception):
  """
  This exception is raised when a package is supposed to be loaded with
  #Loader.load_package() or #Loader.add_package() but another package with
  a different version has already been loaded.
  """

  def __init__(self, package_name, version, loaded_versions):
    self.package_name = package_name
    self.version = version
    self.loaded_versions = loaded_versions

  def __str__(self):
    version_t = 'version' if len(self.loaded_versions) == 1 else 'versions'
    return 'can not load "{}@{}" load because package multiplicity is '\
        'disabled and the package is already loaded in {} "{}"'.format(
          self.package_name, self.selector, version_t,
          ','.join(map(str, self.loaded_versions)))


class UnknownDependency(Exception):
  """
  This exception is raised when a #Module `require()`s another #Package that
  is not listed in the dependencies of the #Module#s package that is currently
  executed.

  Note that the exception is only thrown if #Loader.allow_unknown_dependencies
  is not enabled.
  """

  def __init__(self, source_package, package_name):
    self.source_package = source_package
    self.package_name = package_name

  def __str__(self):
    return '"{}" required "{}" which is not a known dependency'.format(
        self.source_package.identifier, self.package_name)


class PackageManifest:
  """
  This class describes a `cpm.json` package manifest in memory. The manifest
  can have the following fields:

  - name (required)
  - version (required)
  - description
  - dependencies
  - python-dependencies
  - scripts
  - XXX-specific

  The *XXX-specific* field can appear multiple times with *XXX* being an
  arbitrary string. The JSON data of these fields will be stored in the
  #PackageManifest.specifics dictionary. The field can be used by packages that
  are used with applications that are built on top of cpm.

  # Additional Members

  - **is_main_package** (bool): This member can not be specified in the actual
    manifest, but it can be set by the #Finder to indicate that the manifest
    was read from the location where the main package is to be found.
  """

  schema = {
    "type": "object",
    "required": ["name", "version"],
    "properties": {
      "name": {"type": "string"},
      "version": {"type": "string"},
      "description": {"type": "string"},
      "author": {"type": "string"},
      "license": {"type": "string"},
      "main": {"type": "string"},
      "dependencies": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "python-dependencies": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "scripts": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      ".*-specific": {},
    },
    "additionalProperties": False
  }

  @staticmethod
  def parse(directory):
    """
    Parses the `cpm.json` file in the specified *directory* and returns a
    #PackageManifest object for it.

    # Raises
    NotAPackageDirectory: If *directory* does not contain a `cpm.json` file.
    InvalidPackageManifest: If the `cpm.json` file is invalid.
    """

    filename = os.path.join(directory, 'cpm.json')
    if not os.path.isfile(filename):
      raise NotAPackageDirectory(directory)

    with open(filename, 'r') as fp:
      try:
        data = json.load(fp)
      except json.JSONDecodeError as exc:
        raise InvalidPackageManifest(filename, exc)

    try:
      jsonschema.validate(data, PackageManifest.schema)
    except jsonschema.ValidationError as exc:
      raise InvalidPackageManifest(filename, exc)

    try:
      data['version'] = semver.Version(data['version'])
    except ValueError as exc:
      raise InvalidPackageManifest(filename, exc)

    specifics = {}
    for key in tuple(data.keys()):
      if key.endswith('-specific'):
        specific[key[:-9]] = data.pop(key)

    return PackageManifest(filename, **data, specifics=specifics)

  def __init__(self, filename, name, version, description=None, author=None,
      license=None, main='index', dependencies=None, python_dependencies=None,
      scripts=None, specifics=None):
    self.filename = filename
    self.directory = os.path.dirname(filename)
    self.name = name
    self.version = version
    self.author = author
    self.license = license
    self.main = main
    self.description = description
    self.dependencies = {} if dependencies is None else dependencies
    self.python_dependencies = {} if python_dependencies is None else python_dependencies
    self.scripts = {} if scripts is None else scripts
    self.specifics = {} if specifics is None else specifics
    self.is_main_package = False

  def __repr__(self):
    return '<cpm.PackageManifest "{}">'.format(self.identifier)

  @property
  def identifier(self):
    return '{}@{}'.format(self.name, self.version)


class Finder:
  """
  A class to find CPM modules in a set of search directories. It will search
  for `cpm.json` files in the subdirectories of the search path. To clarify,
  here's an example of what would be and what would not be detected by the
  #Finder, given that the only search directory is `cpm_modules/`:

      cpm.json (detected if check_main_package=True, also accesible as #Finder.main)
      cpm_modules/cpm.json  (not detected)
      cpm_modules/some-module/cpm.json (detected)

  # Members

  path (list of str): A list of search directories.
  cache (dict of (str, PackageManifest)): A dictionary that caches the manifest
    information read in for every package directory.
  check_main_package (bool): Parse the main package manifest from the current
    working directory. Defaults to #True. If enabled, the main package's
    #PackageManifest.is_main_package will be set to #True and the manifest
    will be accessible via #Finder.main_package after #update_cache().
  main_package (PackageManifest): If #check_main_package is #True and the
    current working directory exposes a valid manifest, this member will hold
    that #PackageManifest after #update_cache().
  """

  def __init__(self, path=None, check_main_package=True):
    self.path = ['cpm_modules'] if path is None else path
    self.cache = {}
    self.check_main_package = check_main_package
    self.main_package = None

  def add_package(self, directory):
    """
    Manually add a CPM package in *directory* to the #cache. This will allow
    the package to be returned by #find_package() if the criteria matches. If
    the package at *directory* is already in the cache, it will not be
    re-parsed.

    # Return
    PackageManifest
    """

    directory = os.path.normpath(os.path.abspath(directory))
    try:
      manifest = self.cache[directory]
    except KeyError:
      self.cache[directory] = manifest = PackageManifest.parse(directory)
    return manifest

  def update_cache(self):
    """
    This method should be called after the #Finder has been constructed and/or
    after #Finder.path has been modified. Note that removing a path from
    #Finder.path will not remove the cached module information when using this
    method.

    Returns a list of reportable exceptions that occured while searching for
    packages. Most of the time it will be #InvalidPackageManifest exceptions.
    """

    def add(errors, subdir, is_main=False):
      try:
        manifest = self.add_package(subdir)
      except NotAPackageDirectory as exc:
        pass  # We don't mind if it is not a package directory
      except InvalidPackageManifest as exc:
        errors.append(exc)
      else:
        manifest.is_main_package = is_main
        self.main_package = manifest

    errors = []
    if self.check_main_package:
      add(errors, '.', True)
    for directory in self.path:
      if not os.path.isdir(directory):
        continue
      for subdir in os.listdir(directory):
        subdir = os.path.join(directory, subdir)
        if not os.path.isdir(subdir):
          continue

        add(errors, subdir)

    return errors

  def find_packages(self, package_name, selector):
    """
    Find all packages matching the specified *package_name* and the version range
    specified by *selector*. Either and both of the parameters can be #None to
    cause any package or version to be matched, thus using #None for both
    parameters should yield all packages that can be found by the #Finder.

    # Parameters
    package_name (str): The name of the package(s) to find.
    selector (semver.Selector): A selector for a version number range. Only
      packages matching the specified version number range will be returned.

    # Returns
    A generator yielding #PackageManifest objects.
    """

    for manifest in self.cache.values():
      if package_name and manifest.name != package_name:
        continue
      if selector and not selector(manifest.version):
        continue
      yield manifest


class Module(object):
  """
  This class represents an actual Python file in a #Package.
  """

  def __init__(self, package, name, filename):
    self.package = package
    self.name = name
    self.filename = filename
    self.namespace = types.ModuleType(self.identifier)
    self.namespace.__file__ = filename
    self.executed = False

  def __str__(self):
    exec_info = '' if self.executed else ' (not executed)'
    return '<cpm.Module "{}"{}>'.format(self.identifier, exec_info)

  @property
  def is_main(self):
    return self.name == self.package.manifest.main

  @property
  def identifier(self):
    if self.is_main:
      return self.package.identifier
    else:
      return '{}/{}'.format(self.package.identifier, self.name)


class Package:
  """
  This class represents an actual CPM package. When a package or module is
  loaded with #Loader.require(), the respective #Package instance is queried to
  retrieve and return the respective #Module.

  A package can consist of multiple #Module#s but there is always one main
  module that is specified in #PackageManifest.main, which will be loaded when
  the actual package is `require()`d and not any of its components.
  """

  def __init__(self, manifest, module_class=Module):
    self.manifest = manifest
    self.modules = {}
    self.module_class = module_class

  def __str__(self):
    return '<cpm.Package "{}">'.format(self.identifier)

  @property
  def name(self):
    return self.manifest.name

  @property
  def version(self):
    return self.manifest.version

  @property
  def identifier(self):
    return self.manifest.identifier

  def load_module(self, name=None):
    """
    Returns the #Module of this package that matches the specified *name*.
    If *name* is #None, the main module will be returned.
    """

    if name is None:
      name = self.manifest.main
    if name in self.modules:
      return self.modules[name]

    filename = os.path.join(self.manifest.directory, name + '.py')
    filename = os.path.normpath(os.path.abspath(filename))
    if not os.path.isfile(filename):
      raise NoSuchModule(self, name)

    module = self.module_class(self, name, filename)
    self.modules[name] = module
    return module


class Loader:
  """
  This class loads CPM packages that are returned by one or more #Finder#s.
  Similar to normal Python modules, the loaded packages are kept in the
  #packages dictionary. By default, the same package can not be loaded in
  different versions at the same time. To change this behaviour,
  #allow_multiple_versions can be set to #True.

  # Members
  finder (Finder): An object that implements the #Finder interface. By default,
    this is a standard #Finder instance.
  allow_multiple_versions (bool): Allow loading multiple packages of different
    versions with this loader. This behaviour is turned OFF by default.
  allow_unknown_dependencies (bool): Allow dependencies to be `require()`d
    that are not known from the #PackageManifest of the requiring package.
    This behaviour is turned ON by default.
  packages (dict): A dictionary that maps package names to another dictionary.
    This sub-dictionary maps #semver.Version#s to the actual #Package object.
    If #allow_multiple_versions is #False, there will only be one version for
    every package name.
  before_exec (function): A list of functions that will be called before a
    #Module is executed. This function must accept the positional arguments
    (#Loader, #Module).
  module_stack (collections.deque): A stack of the modules that are currently
    being executed. You can retrieve the #Module that is currently being
    executed using the #module property.
  """

  def __init__(self, finder=None, package_class=Package, module_class=Module):
    self.finder = Finder() if finder is None else finder
    self.allow_multiple_versions = False
    self.allow_unknown_dependencies = True
    self.packages = {}
    self.before_exec = []
    self.module_stack = collections.deque()
    self.package_class = package_class
    self.module_class = module_class

  @property
  def module(self):
    if self.module_stack:
      return self.module_stack[-1]
    return None

  def update_cache(self):
    """
    Wrapper for #Finder.update_cache().
    """

    return self.finder.update_cache()

  def add_package(self, manifest):
    """
    Adds a new #Package to the loader from a #PackageManifest. Raises
    #PackageMultiplicityNotAllowed if the #allow_multiple_versions is #False
    and a #Package with the same name but different version is already present.
    """

    have_versions = self.packages.get(manifest.name, {})

    # If we have at least one package with this name but we do not allow
    # loading multiple packages of different versions, error out.
    if have_versions and not self.allow_multiple_versions:
      raise PackageMultiplicityNotAllowed(manifest.name, manifest.version,
          list(have_versions.keys()))

    package = self.package_class(manifest, self.module_class)
    self.packages[manifest.name] = have_versions
    have_versions[manifest.version] = package
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

    # Check if we have already loaded a package that matches the criteria.
    have_versions = self.packages.get(package_name, {})
    if have_versions:
      matches = sorted(filter(selector, have_versions.keys()))
      if matches:
        return have_versions[matches[-1]]

    # Find all available choices.
    choices = list(self.finder.find_packages(package_name, selector))
    if not choices:
      raise PackageNotFound(package_name, selector)

    # And get the best match.
    manifest = selector.best_of(choices, key=lambda x: x.version)
    assert manifest.name == package_name
    return self.add_package(manifest)  # Can raise DuplicatePackage

  def exec_module(self, module):
    """
    Executes a #Module object. If the #Module was already executed, a
    #RuntimeError is raised.
    """

    if not isinstance(module, Module):
      raise TypeError('expected cpm.Module object')
    if module.executed:
      raise RuntimeError('Module already executed')

    with open(module.filename, 'r') as fp:
      code = fp.read()

    module.executed = True
    self.module_stack.append(module)
    try:
      for func in self.before_exec:
        func(self, module)
      code = compile(code, module.filename, 'exec')
      exec(code, vars(module.namespace))
    finally:
      assert self.module_stack.pop() is module

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
      self.exec_module(module)
    return module


class AddVars(object):
  """
  Objects of this class can be added to #Loader.before_exec to initialize
  #Module#s with a default namespace before they are executed.
  """

  def __init__(self, vars=None):
    self.vars = {} if vars is None else vars

  def __call__(self, loader, module):
    vars(module.namespace).update(self.vars)


class AddRequire(object):
  """
  Adds the default `require()` method to the namespace of a #Module before it
  is executed. An instance of this class must be added to #Loader.before_exec.
  Note that the *loader* argument must match the #Loader that this object is
  added to.
  """

  def __init__(self, loader, each_their_own=False):
    self.each_their_own = bool(each_their_own)
    self.require = None if self.each_their_own else Require(loader)

  def __call__(self, loader, module):
    if self.each_their_own:
      require = Require(loader)
    else:
      require = self.require
    module.namespace.require = require


class Require(object):
  """
  Helper class that implements the `require()` function. Use #AddRequire()
  in #Loader.before_exec to add an instance of this class to loaded module's
  namespaces.
  """

  def __init__(self, loader):
    self.loader = loader

  def __call__(self, name):
    module = self.loader.require(name, self.loader.module)
    return module.namespace
