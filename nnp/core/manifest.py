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

__all__ = ['PackageManifest', 'NotAPackageDirectory', 'InvalidPackageManifest']

import json
import jsonschema
import os
from ..utils import semver


class PackageManifest:
  """
  This class describes a `package.json` package manifest in memory. The
  manifest can have the following fields:

  - name (required)
  - version (required)
  - description
  - dependencies
  - python-dependencies
  - scripts
  - bin
  - engines
  - dist

  Additional fields are only accepted when the name of that field also appears
  in the *engines* object, for example

  ```json
  {
    "engines": {
      "python": ">=3.4.1",
      "craftr": ">=3.1.0"
    },
    "craftr": {
      // ...
    }
  }
  ```

  These additional fields are stored in the #engine_props dictionary of the
  #PackageManifest.
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
      "python_dependencies": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "scripts": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "bin": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "engines": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "dist": {
        "type": "object",
        "properties": {
          "include_files": {"type": "array", "items": {"type": "string"}},
          "exclude_files": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False
      }
    },
    "additionalProperties": {"type": "object"}
  }

  @staticmethod
  def parse(directory):
    """
    Parses the `package.json` file in the specified *directory* and returns a
    #PackageManifest object for it.

    # Raises
    NotAPackageDirectory: If *directory* does not contain a `package.json` file.
    InvalidPackageManifest: If the `package.json` file is invalid.
    """

    filename = os.path.join(directory, 'package.json')
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

    engines = {}
    for eng, sel in data.get('engines', {}).items():
      engines[eng] = semver.Selector(sel)
    data['engines'] = engines

    data.setdefault('engines', {})
    engine_props = {}
    for key in tuple(data.keys()):
      if key not in PackageManifest.schema['properties']:
        if key not in data['engines']:
          msg = 'unexpected additional field: "{}"'
          raise InvalidPackageManifest(msg.format(key))
        engine_props[key] = data.pop(key)

    return PackageManifest(filename, **data, engine_props=engine_props)

  def __init__(self, filename, name, version, description=None, author=None,
      license=None, main='index', dependencies=None, python_dependencies=None,
      scripts=None, bin=None, engines=None, engine_props=None, dist=None):
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
    self.bin = {} if bin is None else bin
    self.engine_props = {} if engine_props is None else engine_props
    self.dist = {} if dist is None else dist

  def __repr__(self):
    return '<PackageManifest "{}">'.format(self.identifier)

  @property
  def identifier(self):
    return '{}@{}'.format(self.name, self.version)


class NotAPackageDirectory(Exception):

  def __init__(self, directory):
    self.directory = directory

  def __str__(self):
    return 'Not a package directory: "{}"'.format(self.directory)


class InvalidPackageManifest(Exception):

  def __init__(self, filename, cause):
    self.filename = filename
    self.cause = cause

  def __str__(self):
    return 'In file "{}": {}'.format(self.filename, self.cause)
