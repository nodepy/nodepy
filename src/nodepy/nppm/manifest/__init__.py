# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module provides functionaliy to extract data from a Node.py package
manifest and means to validate its content.
"""

from nodepy.utils import as_text, json
from . import cfgparser
from .. import semver, refstring

import collections
import os
import six

try:
  import pip._internal.req as pip_req
  import pip._internal.exceptions as pip_exceptions
except ImportError:
  import pip.req as pip_req
  import pip.exceptions as pip_exceptions

# A list of strings that are accepted in the manifest's "categories" field.
categories = [
  "CLI",
  "Library",
  "Framework",
  "Application",
  "System",
  "Networking",
  "GUI"
]

# Validators that report errors and warnings for invalid data in a package
# manifest. Add new validators with the #register_validator() function.
validators = {}


Field = collections.namedtuple('Field', 'cfg name value warnings errors')

def register_validator(field_name):
  """
  Decorator to register a validator for the specified *field_name*. If #None
  is specified, the whole package manifest is passed. The decorated function
  must accept a #Field tuple object.
  """
  def decorator(func):
    validators.setdefault(field_name, []).append(func)
    return func
  return decorator


@register_validator('name')
def _validate_name(field):
  try:
    refstring.parse_package(field.value)
  except ValueError as exc:
    field.errors.append(str(exc))


@register_validator('version')
def _validate_version(field):
  try:
    semver.Version(field.value)
  except ValueError as exc:
    field.errors.append(str(exc))


@register_validator('categories')
def _validate_categories(field):
  unknown = [x for x in field.value if x not in categories]
  if unknown:
    field.errors.append('Unsupported categories: {}'.format(', '.join(unknown)))
  if len(field.value) > 5:
    field.errors.append('Packages can only have up to 5 categories.')


@register_validator('keywords')
def _validate_keywords(field):
  if any(1 for x in field.value if len(x) not in range(3, 30)):
    field.errors.append('Keywords must be between 3 and 30 characters.')
  if len(field.value) > 15:
    field.errors.append('Packages can only have up to 15 keywords.')


@register_validator('dependencies')
def _validate_dependencies(field):
  for key, value in field.value.items():
    try:
      Requirement.from_line(value, name=key, expect_name=False)
    except ValueError as exc:
      field.errors.append(str(exc))


@register_validator('pip_dependencies')
def _validate_pip_dependencies(field):
  for key, value in field.value.items():
    try:
      PipRequirement.from_spec(key, value)
    except ValueError as exc:
      field.errors.append(str(exc))


def iter_fields(manifest, name=None):
  """
  Iterates over all fields in the manifest. If no *name* is specified, the
  function will yield tuples of the format `(cfg, name, value)` where *cfg* is
  either #None or the `cfg(...)`string that was associated with the field.

  > Note: That `cfg(...)` string can be suffixed with a dot if the inline
  > format was used, eg. for a field `cfg(...).dependencies`.

  Otherwise, if *name* is specified, only fields matching that name will
  be yielded and the items are tuples of the format `(cfg, value)`.
  """

  if name is not None:
    for cfg, key, value in iter_fields(manifest):
      if key == name:
        yield (cfg, value)
    return

  for key, value in manifest.items():
    if key.startswith('cfg(') and key.endswith(')'):
      if isinstance(value, dict):
        for k, v in value.items(): yield (key, k, v)
        continue
    elif key.startswith('cfg('):
      left, _, right = key.partition('.')
      if left.startswith('cfg(') and left.endswith(')'):
        yield (left + '.', right, value)
        continue
    yield (None, key, value)


def eval_fields(manifest, vars, name=None, default=NotImplemented):
  """
  Evaluates all fields in *manifest*, resolving all `cfg(...)` sections. If
  *name* is specified, only fields with that name are evaluated and only that
  value is returned. *default* must be specified if no #KeyError is to be
  raised when the key does not exist in the manifest without the `cfg(...)`
  part.

  Raises a #ValueError if the innate value of a field is a dictionary but
  an override value that matches via `cfg(...)` is not.

  Dictionaries will be merged. Lists will be concatenated if the first
  element in the list is the string `'<super>'`.

  The returned manifest may contain new warnings. Warnings from the old
  manifest will not be inherited.
  """

  warnings = []

  def eval_cfg(cfg, name, has_value, new_value):
    assert cfg is None or cfg.startswith('cfg(')

    if has_value is NotImplemented or cfg is None:
      if isinstance(new_value, dict):
        return new_value.copy()
      elif isinstance(new_value, list):
        return new_value[:]
      else:
        return new_value

    match, errors = test_cfg(cfg, vars)
    for error in errors:
      warnings.append(Manifest.Warning(cfg, name, error))

    if match:
      if isinstance(has_value, dict):
        if not isinstance(new_value, dict):
          raise ValueError('field ({!r}, {!r}) must be a dictionary since '
            'base value is, got {} instead'.format(cfg, name, type(v).__name__))
        has_value.update(new_value)
        return has_value
      elif isinstance(new_value, list) and new_value and new_value[0] == '<super>':
        if not isinstance(has_value, list):
          raise ValueError('field ({!r}, {!r}) is a list but can not '
            'inherit from {}'.format(cfg, name, type(has_value).__name__))
        return has_value + new_value
      return new_value

    return has_value

  if name is not None:
    has_value = default
    for cfg, new_value in iter_fields(manifest, name):
      has_value = eval_cfg(cfg, name, has_value, new_value)
    return has_value

  result = Manifest(getattr(manifest, 'directory', None))
  for cfg, name, value in iter_fields(manifest):
    has_value = result.get(name, NotImplemented)
    result[name] = eval_cfg(cfg, name, has_value, value)

  result.warnings = warnings
  return result


def test_cfg(s, vars):
  """
  Tests a configuration filter string and returns #True if it matches with
  the dictionary *vars*, #False otherwise. For a specification of the strings
  format, check out the manifest documentation.

  Returns a tuple of (match, errors).
  """

  os = s
  if s.startswith('cfg('):
    if s.endswith('.'): s = s[:-1]
    if not s.endswith(')'):
      raise ValueError('invalid cfg-filter string: {!r}'.format(os))
    s = s[4:-1]

  ctx = cfgparser.Context(vars)
  ast = cfgparser.parse(s)
  return ast.eval(ctx), ctx.errors


def load(file, sorted=True, directory=None):
  """
  Loads a JSON manifest from the specified *file*. The file may be a filename
  or a file-like object. With *sorted* set to #True, the JSON will be loaded
  into a #collections.OrderedDict.
  """

  if isinstance(file, six.string_types):
    file = open(file, 'r')
    close = True
  else:
    close = False

  if not directory and getattr(file, 'name', None):
    directory = os.path.dirname(os.path.abspath(file.name))

  object_hook = collections.OrderedDict if sorted else None
  try:
    return Manifest(directory, json.load(file, object_pairs_hook=object_hook))
  finally:
    if close:
      file.close()


def validate(payload):
  """
  Apply all registered #validators for the manifest *payload*. A list of
  #Field objects will be returned for which at least one warning or error
  was issued.
  """

  fields = []
  for cfg, name, value in iter_fields(payload):
    field = Field(cfg, name, value, [], [])
    for valfunc in validators.get(name, []):
      valfunc(field)
    if field.warnings or field.errors:
      fields.append(field)
  return fields


class Manifest(collections.OrderedDict):

  Warning = collections.namedtuple('Warning', 'cfg name message')

  def __init__(self, directory, *args, **kwargs):
    super(Manifest, self).__init__(*args, **kwargs)
    self.directory = directory
    self.warnings = []

  @property
  def identifier(self):
    return '{}@{}'.format(self['name'], self.get('version', '*'))

  def iter_fields(self, name=None):
    return iter_fields(self, name)

  def eval_fields(self, vars, name=None, default=NotImplemented):
    return eval_fields(self, vars, name, default)


class PipRequirement(pip_req.InstallRequirement):

  @classmethod
  def from_line(cls, line, *args, **kwargs):
    try:
      if hasattr(super(PipRequirement, cls), 'from_line'):
        return super(PipRequirement, cls).from_line(line, *args, **kwargs)
      else:
        obj = pip_req.constructors.install_req_from_line(line, *args, **kwargs)
        obj.__class__ = cls
        return obj
    except pip_exceptions.InstallationError:
      raise ValueError('invalid Pip requirement: {!r}'.format(line))

  @classmethod
  def from_spec(cls, key, value):
    try:
      return cls.from_line(value)
    except ValueError:
      return cls.from_line(key + value)


class Requirement(object):
  """
  Represents a Node.py dependency. The default value of all flags are #None,
  which indicates that the flag may inherit the value from somewhere else.
  """

  FLAGS = ('pure', 'internal', 'link', 'optional', 'recursive')
  OPTIONS = ('registry',)

  def __init__(self, name, selector=None, path=None, git_url=None,
               pure=None, internal=None, link=None, optional=None,
               recursive=False, registry=None):
    assert isinstance(selector, semver.Selector) or selector is None, selector
    self.name = as_text(name) if name is not None else None
    self.selector = selector
    self.path = as_text(path) if path is not None else None
    self.git_url = git_url
    self.pure = pure
    self.internal = internal
    self.link = link
    self.optional = optional
    self.recursive = recursive
    self.registry = as_text(registry) if registry is not None else None

  def __str__(self):
    parts = []
    for flag in self.FLAGS:
      if getattr(self, flag):
        parts.append('--{}'.format(flag))
    for key in self.OPTIONS:
      value = getattr(self, key)
      if value:
        parts.append('--{}={}'.format(key, value))
    name = (self.name + '@' if self.name else '')
    if self.selector:
      name += str(self.selector)
    elif self.path:
      name += self.path
    elif self.git_url:
      name += 'git+' + self.git_url
    parts.append(name)
    return ' '.join(parts)

  @property
  def type(self):
    if self.path:
      return 'path'
    elif self.git_url:
      return 'git'
    elif self.name:
      return 'registry'
    else:
      raise RuntimeError('this requirement is empty')

  def inherit_values(self, pure=False, internal=False, link=False,
                     optional=False, recursive=True, registry=None):
    """
    Update the flags and options of the requirement with default values.
    Only fields with #None values are updated.
    """

    for key in self.FLAGS + self.OPTIONS:
      if getattr(self, key) is None:
        setattr(self, key, locals()[key])

  @classmethod
  def from_line(cls, line, *args, **kwargs):
    """
    Parse a line that contains the all information about the requirement.

    # Parameter
    line (str): The line to parse.
    *args, **kwargs: Additional arguments passed to the #Requirement
        constructor.
    expect_name (bool): #True if a name is expected to be parsed from the
        *line*, #False otherwise.
    name (str): The name if no name is expected to be parsed from *line*.
    """

    name = kwargs.pop('name', None)
    expect_name = kwargs.pop('expect_name', True)
    original_line = line = line.strip()

    # Parse the flags.
    kwargs = {}
    while line.startswith('--'):
      index = line.index(' ')
      if index < 0:
        raise ValueError('invalid requirement: {!r}'.format(original_line))
      flag, _, value = line[2:index].partition('=')
      if value and flag not in cls.OPTIONS:
        raise ValueError('invalid option "{}" in {!r}'.format(flag, original_line))
      if not value and flag not in cls.FLAGS:
        raise Validators('invalid flag "{}" in {!r}'.format(flag, original_line))
      kwargs[flag] = value if value else True
      line = line[index+1:].lstrip()

    if expect_name and not cls._is_path(line) and '@' in line:
      left, _, right = line.partition('@')
      if not left.startswith('git+'):
        name = left
        line = right.rstrip()

    if line.startswith('git+'):
      kwargs['git_url'] = line[4:]
    elif cls._is_path(line):
      kwargs['path'] = line
    else:
      kwargs['selector'] = semver.Selector(line)

    if 'registry' in kwargs and 'selector' not in kwargs:
      raise ValueError('invalid requirement (--registry can only be specified '
        ' for dependencies that need to be resolved in a registry): {!r}'
        .format(original_line))

    return cls(name, **kwargs)

  @staticmethod
  def _is_path(s):
    return (s == '.' or s == '..' or
            s.startswith('./') or s.startswith('.\\') or
            s.startswith('../') or s.startswith('..\\') or
            os.path.isabs(s))
