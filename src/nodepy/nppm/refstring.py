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

import collections
import re

from . import argschema, semver, manifest

spec = '[[@<scope>/]<name>[@<version>]][/<module>][:<member>]'

regex = re.compile('''^
  (?:
    (?: @(?P<scope>   [A-z0-9\.\-_]+)/)?
    (?P<name>    [A-z0-9\.\-_]+)
    (?: @(?P<version> [^/:]*))?          # Version is actually a semver.Selector
  )?
  (?: /(?P<module>   [A-z0-9\.\-_]+))?
  (?: :(?P<member> [A-z0-9\.\-_]+))?
  $''', re.X)

package_regex = re.compile('^(?:@([A-z0-9\.\-_]+)/)?([A-z0-9\.\-_]+)$')


class Ref(object):
  """
  Represents a the contents of a reference string. Note that the #version
  member of a #PackageRef is always a #semver.Selector, if it is set.
  """

  def __init__(self, package, version, module, member):
    argschema.validate('package', package, {'type': [None, Package]})
    argschema.validate('version', version, {'type': [None, str, semver.Selector]})
    argschema.validate('module', module, {'type': [None, str]})
    argschema.validate('member', member, {'type': [None, str]})

    if not package and version:
      raise ValueError('can not specify version without package name')
    if isinstance(version, str):
      version = semver.Selector(version)

    self.package = package
    self.version = version
    self.module = module
    self.member = member

  def __bool__(self):
    return any((self.package, self.version, self.module, self.member))

  __nonzero__ = __bool__

  def __str__(self):
    package = self.package
    if package:
      result = str(package)
      if self.version:
        result += '@' + str(self.version)
    else:
      if self.version:
        raise ValueError('version can not be specified without a package')
      result = ''
    if self.module:
      result += '/' + self.module
    if self.member:
      result += ':' + self.member
    return result

  def __unicode__(self):
    return unicode(str(self))

  def __repr__(self):
    return '<Ref "{}">'.format(self)

  def __eq__(self, other):
    if isinstance(other, Ref):
      return (self.package, self.version, self.module, self.member) == \
          (other.package, other.version, other.module, other.member)
    return False


class Package(object):
  """
  Represents a package identifier.
  """

  def __init__(self, scope, name):
    if name in ('.', '..'):
      raise ValueError('invalid package name: {!r}'.format(name))
    if not name and scope:
      raise ValueError('package name can not consist of only a scope')
    self.scope = scope
    self.name = name

  def __str__(self):
    if self.scope:
      return '@{}/{}'.format(self.scope, self.name)
    return self.name

  def __unicode__(self):
    return unicode(str(self))

  def __iter__(self):
    yield self.scope
    yield self.name

  def __eq__(self, other):
    if isinstance(other, Package):
      return (self.scope, self.name) == (other.scope, other.name)


def parse(s):
  """
  Parse a reference string and returns a #Ref object. If the reference string
  is invalid, a #ValueError is raised.
  """

  m = regex.match(s)
  if not m:
    raise ValueError('invalid refstring: "{}"'.format(s))
  scope, name, version, module, member = m.groups()
  package = Package(scope, name) if (scope or name) else None
  try:
    return Ref(package, version, module, member)  # can be raised for the version selector
  except ValueError as exc:
    raise ValueError('invalid refstring: "{}"'.format(exc))


def parse_package(s):
  """
  Parse only a package name of the format `[@<scope>/]<name>`. Returns a
  tuple of (scope, name).
  """

  m = package_regex.match(s)
  if not m:
    raise ValueError('invalid package name: {!r}'.format(s))
  return Package(*m.groups())


def join(package=None, version=None, module=None, member=None):
  if package is not None:
    package = parse_package(str(package))
  return str(Ref(package, version, module, member))
