# Copyright (c) 2017  Niklas Rosenstein
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

import functools
import re
import six


@functools.total_ordering
class Version(object):
  """
  Represents a SemVer of the format `MAJOR.MINOR.PATCH-EXTENSION+BUILD`, where
  the `EXTENSION` and `BUILD` parts are optional.

  # Attributes
  major (int):
  minor (int):
  patch (int):
  extension (six.text_type):
  build (six.text_type):
  """

  def __init__(self, value):
    if isinstance(value, six.binary_type):
      value = six.text_type(value)
    if isinstance(value, Version):
      self.major = value.major
      self.minor = value.minor
      self.patch = value.patch
      self.extension = value.extension
      self.build = value.build
    elif isinstance(value, six.text_type):
      match = re.match(r'^(\d+(\.\d+){0,2})(\-[A-z\-][A-z0-9\-]*)?(\+[A-z\-][A-z0-9\-]*)?$', value)
      if not match:
        raise ValueError("invalid version string: {0!r}".format(value))
      parts = [int(x) for x in match.group(1).split('.')]
      parts.extend(0 for __ in range(3 - len(parts)))
      self.major, self.minor, self.patch = parts
      self.extension = match.group(3)
      self.build = match.group(4)
      if self.extension is not None:
        self.extension = self.extension[1:]
      if self.build is not None:
        self.build = self.build[1:]
    else:
      raise TypeError("unexpected type: {0!r}".format(type(value)))

  def __str__(self):
    result = '.'.join(map(six.text_type, self.mmp))
    if self.extension:
      result += '-' + self.extension
    if self.build:
      result += '+' + self.build
    return result

  def __repr__(self):
    return '<Version "{}">'.format(self)

  def __lt__(self, other):
    if isinstance(other, Version):
      # Check if any of the minor, major and patch differ.
      for a, b in zip(self.mmp, other.mmp):
        if a < b:
          return True
        elif a > b:
          return False
      # If not, both minor, major and patch numbers must be equal.
      assert self.mmp == other.mmp
      # A SemVer without an extension are to be preferred over a SemVer
      # with extension.
      if other.extension:
        if self.extension:
          return self.extension < other.extension
        else:
          return False
      else:
        if self.extension:
          return True
      return False
    else:
      return NotImplemented

  def __eq__(self, other):
    if isinstance(other, Version):
      return self.mmpeb == other.mmpeb
    else:
      return NotImplemented

  def __hash__(self):
    return hash(six.text_type(self))

  @property
  def mmp(self):
    return (self.major, self.minor, self.patch)

  @property
  def mmpeb(self):
    return (self.major, self.minor, self.patch, self.extension, self.build)

  def satisfies(self, selector):
    if isinstance(selector, six.text_type):
      selector = Selector(selector)
    elif not callable(selector):
      raise TypeError("selector: expected unicode or callable")
    return selector(self)


class SingleSelector(object):

  operators = {
    '*':  None,
    '-':  None,
    'x':  None,
    '=':  lambda a, b: a == b,
    '<':  lambda a, b: a <  b,
    '<=': lambda a, b: a <= b,
    '>':  lambda a, b: a >  b,
    '>=': lambda a, b: a >= b,
    '~':  lambda a, b: a.major == b.major and a.minor == b.minor and a >= b,
    '^':  lambda a, b: a.major == b.major and a >= b,
  }

  def __init__(self, value, version=None):
    if isinstance(value, six.binary_type):
      value = six.text_type(value)
    if isinstance(value, six.text_type) and '-x' not in value:
      try:
        value = Version(value)
      except ValueError as exc:
        pass

    self.parts = None
    if isinstance(value, SingleSelector):
      self.op = value.op
      self.version = version(value.version)
      self.version_min = None

    elif isinstance(value, six.text_type):
      # Split into parts to check if its a range selector.
      parts = re.sub('\s+', ' ', value).split(' ')
      if len(parts) == 3 and parts[1] == '-':
        assert version is None
        self.op = '-'
        self.version_min = Version(parts[0])
        self.version = Version(parts[2])
      elif value in self.operators:
        self.op = value
        if value == '*':
          assert version is None
          self.version = self.version_min = None
        elif value == '-':
          if isinstance(value, (list, tuple)):
            self.version_min, self.version = map(Version, value)
          else:
            assert version is None
            self.version_min = self.version = None
        elif value == 'x':
          raise TypeError("can not explicitly initialize with 'x' operator")
        else:
          # Unary operator
          self.version = Version(version)
          self.version_min = None
      elif 'x' in value:
        # Placeholder version number.
        parts = value.split('.')
        if not parts or len(parts) > 3:
          raise ValueError('invalid version format: "{0}"'.format(value))
        if '-' in parts[-1]:
          parts[-1], ext = parts[-1].split('-', 1)
          parts.append(ext)
        parts += ['x' for __ in range(3 - len(parts))]
        if len(parts) < 4: parts.append('x')
        try:
          if len(parts) > 4: raise ValueError
          parts[:-1] = [int(p) if p != 'x' else 'x' for p in parts[:-1]]
        except ValueError:
          raise ValueError("invalid placeholder selector: {0!r}".format(value))
        self.op = 'x'
        self.parts = parts
        self.version = None
        self.version_min = None
      else:
        # Match unary operators.
        match = re.match(r'^(=|<=?|>=?|\^|~)(.*)$', value)
        if not match:
          raise ValueError("invalid version selector: {0!r}".format(value))
        if match.group(2):
          assert version is None
          version = match.group(2).strip()
        if version is not None:
          version = Version(version)
        self.op = match.group(1)
        self.version = version
        self.version_min = None

      if self.op not in ('*', 'x') and self.version is None:
        raise ValueError('operator {0!r} requires version argument'.format(self.op))
      elif self.op == '*' and self.version is not None:
        raise ValueError('operator * does not allow version argument')
      elif self.op == '-' and (self.version is None or self.version_min is None):
        raise ValueError('range operator requires left and right version')
      assert self.op in self.operators

    elif isinstance(value, Version):
      self.version = Version(value)
      if version is None:
        self.op = '='
        self.version_min = None
      else:
        self.op = '-'
        self.version_min = Version(version)

    else:
      raise TypeError("value: expected SingleSelector, Version or unicode")

  def __str__(self):
    if self.op == '*':
      return '*'
    elif self.op == '-':
      return '{0} - {1}'.format(self.version_min, self.version)
    elif self.op == 'x':
      mmp, ext = self.parts[:3], self.parts[3:]
      result = '.'.join(map(six.text_type, self.parts[:3]))
      if ext:
        result += '-' + ext[0]
      return result
    else:
      return '{0}{1}'.format(self.op, self.version)

  def __call__(self, version):
    if not isinstance(version, Version):
      raise TypeError('version: expected Version')
    if self.op == '*':
      return True
    elif self.op == '-':
      return self.version_min <= version and version <= self.version
    elif self.op == 'x':
      for pcmp, vcmp in zip(self.parts, version.mmpeb):
        if pcmp != 'x' and pcmp != vcmp:
          return False
      return True
    else:
      return self.operators[self.op](version, self.version)

  def __eq__(self, other):
    if isinstance(other, SingleSelector):
      return (self.parts, self.op, self.version_min) == \
          (other.parts, other.op, other.version_min)
    else:
      return False

  def __ne__(self, other):
    return not (self == other)


class Selector(object):
  """
  This class implements a filter for version numbers by the following schema:

      *        := Match any version
      =  V     := Matches a specific version
      <  V     := Match a version that is older than V
      <= V     := Match a version that is older than or equal to V
      >  V     := Match a version that is newer than V
      >= V     := Match a version that is newer than or equal to V
      ~  V     := Match a version with the same major and minor release as V
                  that is also equal to or newer than V
      ^  V     := Match a version with the same major release as V that is
                  also equal to or newer than V
      V1 - V2  := Match any version number between (including) V1 and V2
                  (mind the whitespace around the hyphen!)
      x.x.x-x  := Match a version where "x" can be any number. These
                  placeholders can be placed anywhere, like "x.9.1"
                  or "1.x". Any components that are left out will be
                  filled with placeholders.

  For example, to specify a version that will receive all bug fixes
  and patches, you can use `~2.1.3`. Multiple selectors can be concatened
  using double pipes (`||`) as in `=1.0 || >2.5 || 0.9 - 1.3.0-rc1`.
  """

  def __init__(self, value):
    if isinstance(value, six.binary_type):
      value = six.text_type(value)
    if isinstance(value, Selector):
      self.criteria = [SingleSelector(x) for x in value.criteria]
    elif isinstance(value, Version):
      self.criteria = [SingleSelector(value)]
    elif isinstance(value, six.text_type):
      items = filter(bool, value.split('||'))
      self.criteria = [SingleSelector(x.strip()) for x in items]
    else:
      raise TypeError('value: expected Selector or unicode')
    if not self.criteria:
      raise ValueError('invalid Selector: {!r}'.format(value))

  def __str__(self):
    return ' || '.join(map(six.text_type, self.criteria))

  def __repr__(self):
    return '<%s %s>' % (type(self).__name__, six.text_type(self))

  def __call__(self, version):
    return any(c(version) for c in self.criteria)

  def __len__(self):
    return len(self.criteria)

  def __eq__(self, other):
    if isinstance(other, Selector):
      return self.criteria == other.criteria
    else:
      return False

  @property
  def fixed_version(self):
    """
    If the Selector matches one specific version only, returns that version.
    Returns None in any other case.
    """

    if len(self.criteria) == 1 and self.criteria[0].op == '=':
      return self.criteria[0].version
    return None

  def best_of(self, versions, key=None):
    """
    Given a list of versions, selects the best (aka. newest) version that
    matches this selector. If there is no version matching the selector,
    #None will be returned instead.
    """

    key = (lambda x: x) if key is None else key
    if not callable(key):
      raise TypeError('key must be callable')

    best = None
    best_version = None
    for obj in versions:
      obj_version = key(obj)
      if self(obj_version) and (best_version is None or obj_version > best_version):
        best = obj
        best_version = obj_version

    return best
