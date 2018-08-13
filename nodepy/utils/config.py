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
Access to the Node.py configuration (which can also be used by other
components, eg. nodepy-pm). The configuration is parsed using the Python
`configparser` (or `ConfigParser` in Python 2) module, however global
configuration values are (in theory) support and will be added to the
section with the name `__global__`.

Example:

    key1 = Value 1

    [section1]
    key2 = Value 2

This configuration contains the keys `__global__.key1` and `section1.key2`.
"""

from six.moves import configparser
import errno
import getpass
import os
import re
import sys

try:
  from cStringIO import StringIO
except ImportError:
  try:
    from StringIO import StringIO
  except ImportError:
    from io import StringIO


class NoSuchSection(KeyError):
  pass


class Config(object):
  """
  Wraps a #configparser.SafeConfigParser object and normalizes registry
  section names as well as creating a default `__global__` section at the
  start.
  """

  NoSuchSection = NoSuchSection

  def __init__(self, filename, defaults=None):
    self.filename = filename
    if sys.version <= '3.2':
      parser_class = configparser.SafeConfigParser
    else:
      # SafeConfigParser was renamed to ConfigParser, SafeConfigParser is
      # deprecated.
      parser_class = configparser.ConfigParser
    self._parser = parser_class()
    self.defaults = defaults or {}
    self.read(filename, doraise=False)

  def read(self, filename, doraise=True):
    if not doraise and not os.path.isfile(filename):
      return
    with open(filename) as fp:
      return self.readfp(fp)

  def readfp(self, fp):
    fp = StringIO('[__global__]\n' + fp.read())
    self._parser.readfp(fp)

  def save(self):
    buf = StringIO()
    self._parser.write(buf)
    buf.seek(0)
    assert buf.readline() == '[__global__]\n'
    with open(self.filename, 'w') as dst:
      dst.write(buf.read())

  def __getitem__(self, key):
    section, sep, valuename = key.partition('.')
    if not valuename:
      section, valuename = '', section
    if not section and sep:
      raise KeyError(key)
    if not section:
      section = '__global__'
    if not self._parser.has_section(section):
      if section not in self.defaults:
        raise KeyError(key)
      return self.defaults[section][valuename]
    if not self._parser.has_option(section, valuename):
      if section in self.defaults:
        return self.defaults[section][valuename]
      raise KeyError(key)
    return self._parser.get(section, valuename)

  def __setitem__(self, key, value):
    section, sep, valuename = key.partition('.')
    if not section and sep:
      raise KeyError(key)
    if not section:
      section = '__global__'
    if not self._parser.has_section(section):
      self._parser.add_section(section)
    self._parser.set(section, valuename, value)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def sections(self):
    return self._parser.sections()

  def section(self, name):
    if not self.has_section(name):
      raise NoSuchSection(name)
    return SectionView(self, name)

  def has_section(self, name):
    if self._parser.has_section(name):
      return True
    return name in self.defaults


class SectionView(object):

  def __init__(self, config, name, section_prefix=None):
    self.config = config
    self.name = name
    self.section_prefix = section_prefix or name

  def __repr__(self):
    return '<SectionView {!r}>'.format(self.section_prefix)

  def __getitem__(self, key):
    return self.config[self.section_prefix + '.' + key]

  def __setitem__(self, key, value):
    self.config[self.section_prefix + '.' + key] = value

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default


def read_config(filename, defaults=None):
  """
  Reads the configuration from the path given with *filename*.
  """

  return Config(filename, defaults)
