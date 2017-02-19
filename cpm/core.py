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

import collections
import json
import jsonschema
import os
import posixpath
import shutil
import textwrap
import types

from .exceptions import *
from .utils import semver


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
      "exclude_files": {
        "type": "array",
        "items": {"type": "string"}
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

    dependencies = {}
    for dep, sel in data.get('dependencies', {}).items():
      dependencies[dep] = semver.Selector(sel)
    data['dependencies'] = dependencies

    specifics = {}
    for key in tuple(data.keys()):
      if key.endswith('-specific'):
        specific[key[:-9]] = data.pop(key)

    return PackageManifest(filename, **data, specifics=specifics)

  def __init__(self, filename, name, version, description=None, author=None,
      license=None, main='index', dependencies=None, python_dependencies=None,
      scripts=None, exclude_files=None, specifics=None):
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
    self.exclude_files = [] if exclude_files is None else exclude_files

  def __repr__(self):
    return '<cpm.PackageManifest "{}">'.format(self.identifier)

  @property
  def identifier(self):
    return '{}@{}'.format(self.name, self.version)


class Finder:
  """
  Interface for package finders.
  """

  def find_package(self, package_name, version_selector):
    """
    Find a #PackageManifest for a given *package_name* and *version_selector*.
    If multiple packages matching the criteria are found, the best matching
    (aka. newest) version number should be returned.

    # Raises
    PackageNotFound:
    """

class DefaultFinder(Finder):
  """
  A class to find packages in a directory. Packages must be sub-directories of
  the actual search-directory that contain a `cpm.json` file. Below is an
  example of which files can be detected given that the search directory is
  `cpm_modules/`.

      cpm.json (not detected)
      cpm_modules/cpm.json  (not detected)
      cpm_modules/some-module/cpm.json (detected)

  # Members

  directory (str): The directory to search for modules.
  cache (dict of (str, PackageManifest)): A dictionary that caches the manifest
    information read in for every package directory.
  """

  def __init__(self, directory):
    self.directory = directory
    self.cache = {}

  def load_package_manifest(self, directory):
    """
    Manually add a CPM package in *directory* to the #cache. This will allow
    the package to be returned by #find_package() if the criteria matches. If
    the package at *directory* is already in the cache, it will not be
    re-parsed.

    # Raise
    NotAPackageDirectory:
    InvalidPackageManifest:

    # Return
    PackageManifest:
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
        self.load_package_manifest(subdir)
      except NotAPackageDirectory as exc:
        pass  # We don't mind if it is not a package directory
      except InvalidPackageManifest as exc:
        errors.append(exc)

    errors = []
    if os.path.isdir(self.directory):
      for subdir in os.listdir(self.directory):
        subdir = os.path.join(self.directory, subdir)
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


class Module:
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

  @property
  def loader(self):
    return self.package.loader

  def exec_(self):
    """
    Executes the #Module object. Raises #RuntimeError if the module has already
    been executed.
    """

    if self.executed:
      raise RuntimeError('Module already executed')

    with open(self.filename, 'r') as fp:
      code = fp.read()

    self.executed = True
    self.loader.module_stack.append(self)
    try:
      for func in self.loader.before_exec:
        func(self)
      code = compile(code, self.filename, 'exec')
      exec(code, vars(self.namespace))
    finally:
      assert self.loader.module_stack.pop() is self


class Package:
  """
  This class represents an actual CPM package. When a package or module is
  loaded with #Loader.require(), the respective #Package instance is queried to
  retrieve and return the respective #Module.

  A package can consist of multiple #Module#s but there is always one main
  module that is specified in #PackageManifest.main, which will be loaded when
  the actual package is `require()`d and not any of its components.
  """

  def __init__(self, manifest, loader):
    self.manifest = manifest
    self.modules = {}
    self.loader = loader

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

  @property
  def directory(self):
    return self.manifest.directory

  @property
  def is_installed(self):
    """
    Returns #True if the package is an installed package (that is, if there
    exists an `.installed-files` file).
    """

    fn = os.path.join(self.directory, '.installed-files')
    return os.path.isfile(fn)

  def get_installed_files(self):
    with open(os.path.join(self.directory, '.installed-files')) as fp:
      return list(filter(bool, [x.rstrip('\n') for x in fp]))

  def uninstall(self):
    if not self.is_installed:
      raise RuntimeError("this is not an installed package")
    files = self.get_installed_files()
    shutil.rmtree(self.directory)
    for filename in files:
      if os.path.isfile(filename):
        os.remove(filename)

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

    module = self.loader.module_class(self, name, filename)
    self.modules[name] = module
    return module


class Loader:
  """
  This class can load CPM packages from #PackageManifest data. Similar to
  normal Python modules, the loaded packages are kept in a #packages
  dictionary. By default, the same package can not be loaded in different
  versions at the same time. To change this behaviour, #allow_multiple_versions
  can be set to #True.

  It is very common to initialize the namespace of modules that are being
  with default members before they are executed. This can be achived by adding
  function objects to the #before_exec list. Each of the functions in this
  list will be called with the #Module that is about to be executed.

  # Members
  allow_multiple_versions (bool): Allow loading multiple packages of different
    versions with this loader. This behaviour is turned OFF by default.
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

  def __init__(self, package_class=Package, module_class=Module):
    self.allow_multiple_versions = False
    self.packages = {}
    self.before_exec = []
    self.module_stack = collections.deque()
    self.package_class = package_class
    self.module_class = module_class

  def get_current_module(self):
    if self.module_stack:
      return self.module_stack[-1]
    return None

  def get_packages(self, package_name, selector):
    """
    Get a list of all packages matching the *package_name* and version
    *selector*. The list is sorted by the most preferable package first
    (sorted by version number).
    """

    have_versions = self.packages.get(package_name, {})
    return sorted(have_versions.values(), key=lambda x: x.version)

  def load_package(self, manifest):
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

    package = self.package_class(manifest, self)
    self.packages[manifest.name] = have_versions
    have_versions[manifest.version] = package
    return package
