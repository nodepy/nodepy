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

import json
import jsonschema
import os
import re
import six

semver = require('./semver')
refstring = require('./refstring')

# Django's URL validation regex.
url_regex = re.compile(
  r'^(?:http|ftp)s?://' # http:// or https://
  r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
  r'localhost|' #localhost...
  r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
  r'(?::\d+)?' # optional port
  r'(?:/?|[/?]\S+)$', re.IGNORECASE)


class PackageManifest:
  """
  This class describes a `package.json` package manifest in memory. The
  manifest can have the following fields:

  - name (required)
  - version (required)
  - license
  - description
  - repository
  - bin
  - script
  - engines
  - dependencies
  - python-dependencies
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
      "repository": {"type": "string"},
      "license": {"type": "string"},
      "dependencies": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "python-dependencies": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "script": {
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
      },
      "postinstall": {"type": "string"}
    },
    "additionalProperties": {"type": "object"}
  }

  def __init__(self, filename, directory, name, version, description=None,
      author=None, license=None, dependencies=None, python_dependencies=None,
      script=None, bin=None, engines=None, engine_props=None, dist=None,
      postinstall=None, repository=None):
    if repository is not None and not url_regex.match(repository):
      raise ValueError('invalid repository: "{}" is not a URL'.format(repository))
    self.filename = filename
    self.directory = directory
    self.name = name
    self.version = version
    self.author = author
    self.repository = repository
    self.description = description
    self.license = license
    self.dependencies = {} if dependencies is None else dependencies
    self.python_dependencies = {} if python_dependencies is None else python_dependencies
    self.script = {} if script is None else script
    self.bin = {} if bin is None else bin
    self.engine_props = {} if engine_props is None else engine_props
    self.dist = {} if dist is None else dist
    self.postinstall = postinstall

  def __eq__(self, other):
    if isinstance(other, PackageManifest):
      return (self.filename, self.directory, self.name, self.version) == \
          (other.filename, other.directory, other.name, other.version)
    return False

  def __ne__(self, other):
    return not (self == other)

  def __repr__(self):
    return '<PackageManifest "{}">'.format(self.identifier)

  @property
  def identifier(self):
    return '{}@{}'.format(self.name, self.version)


class InvalidPackageManifest(Exception):
  """
  Raised from #parse() and #parse_dict() when the JSON data is does not
  match the #PackageManifest.schema and the additional constraints, or if
  the parsed file is not valid JSON.
  """

  def __init__(self, filename, cause):
    self.filename = filename
    self.cause = cause

  def __str__(self):
    if self.filename:
      return 'In file "{}": {}'.format(self.filename, self.cause)
    return str(self.cause)



def parse(filename, directory=None):
  """
  Parses a manifest file and returns it. If *directory* is #None, it will
  be derived from the *filename*.

  # Raises
  InvalidPackageManifest: If the `package.json` file is invalid.
  """

  if not directory:
    directory = os.path.dirname(filename) or '.'
  with open(filename, 'r') as fp:
    try:
      data = json.load(fp)
    except json.JSONDecodeError as exc:
      raise InvalidPackageManifest(filename, exc)
    return parse_dict(data, filename, directory, copy=False)


def parse_dict(data, filename=None, directory=None, copy=True):
  """
  Takes a Python dictionary that represents a manifest from a JSON source
  and converts it to a #PackageManifest. The *filename* and *directory* can
  be set to #None depending on whether you want the respective members in
  the #PackageManifest to be #None.
  """

  try:
    jsonschema.validate(data, PackageManifest.schema)
  except jsonschema.ValidationError as exc:
    raise InvalidPackageManifest(filename, exc)

  if copy:
    data = data.copy()

  # Validate the package name.
  try:
    refstring.parse_package(data['name'])
  except ValueError as exc:
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
        raise InvalidPackageManifest(filename, msg.format(key))
      engine_props[key] = data.pop(key)

  data['python_dependencies'] = data.pop('python-dependencies', None)
  data['engine_props'] = engine_props
  try:
    return PackageManifest(filename, directory, **data)
  except ValueError as exc:
    six.raise_from(InvalidPackageManifest(filename, exc), exc)
