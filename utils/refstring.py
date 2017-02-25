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
import re

semver = require('@ppym/semver')

Ref = collections.namedtuple('Ref', 'package version module member')
spec = '[<package>[@<version>]][/<module>][:<member>]'
regex = re.compile('''^
  (?:
    (?P<package> [A-z0-9\.\-_]+)
    (?: @(?P<version> [^/:]*))?  # Version is actually a semver.Selector
  )?
  (?: /(?P<module>   [A-z0-9\.\-_]+))?
  (?: :(?P<member> [A-z0-9\.\-_]+))?
  $''', re.X)


def parse(s):
  """
  Parse a reference string and returns a #Ref which is a namedtuple consisting
  of the members *package*, *version*, *module* and *member*. The parameter
  *s* must be a string of the format

      [<package>[@<version>]][/<module>][:<member>]

  # Raises
  ValueError: If the string is invalid.
  """

  m = regex.match(s)
  if not m:
    raise ValueError('invalid refstring: "{}"'.format(s))
  package, version, module, member = m.groups()
  if version:
    try:
      version = semver.Selector(version)
    except ValueError as exc:
      raise ValueError('invalid refstring: "{}" ({})'.format(s, exc))
  return Ref(package, version, module, member)


def join(package=None, version=None, module=None, member=None):
  """
  Concatenes the components of a reference back into a string. To use this
  function with a #Ref object, simply use argument-unpacking like this:
  `join(*ref)`.
  """

  if package:
    result = package
    if version:
      result += '@' + str(version)
  else:
    if version:
      raise ValueError('version can not be specified without a package')
    result = ''

  if module:
    result += '/' + module
  if member:
    result += ':' + member

  return result
