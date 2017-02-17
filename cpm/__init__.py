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

import json
import jsonschema
import os
import semver


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
      semver.parse(data['version'])
    except ValueError as exc:
      raise InvalidPackageManifest(filename, exc)

    specifics = {}
    for key in tuple(data.keys()):
      if key.endswith('-specific'):
        specific[key[:-9]] = data.pop(key)

    return PackageManifest(filename, **data, specifics=specifics)

  def __init__(self, filename, name, version, description=None, author=None,
      license=None, dependencies=None, python_dependencies=None, scripts=None,
      specifics=None):
    self.filename = filename
    self.directory = os.path.dirname(filename)
    self.name = name
    self.version = version
    self.author = author
    self.license = license
    self.description = description
    self.dependencies = {} if dependencies is None else dependencies
    self.python_dependencies = {} if python_dependencies is None else python_dependencies
    self.scripts = {} if scripts is None else scripts
    self.specifics = {} if specifics is None else specifics

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

      cpm_modules/cpm.json  (not detected)
      cpm_modules/some-module/cpm.json (detected)
  """

  def __init__(self, path=None):
    self.path = ['cpm_modules'] if path is None else path
    self.cache = {}

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

    errors = []
    for directory in self.path:
      if not os.path.isdir(directory):
        continue
      for subdir in os.listdir(directory):
        subdir = os.path.join(directory, subdir)
        if not os.path.isdir(subdir):
          continue

        try:
          manifest = self.add_package(subdir)
        except NotAPackageDirectory as exc:
          pass  # We don't mind if it is not a package directory
        except InvalidPackageManifest as exc:
          errors.append(exc)

    return errors
