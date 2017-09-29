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

NPPM_CONFIG = '~/.nppmrc'


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
    self._parser = configparser.SafeConfigParser()
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

  def rename_section(self, section, new_name):
    items = self._parser.items(section)
    self._parser.remove_section(section)
    self._parser.add_section(new_name)
    for key, value in items:
      self._parser.set(new_name, key, value)

  def section(self, name):
    if not self.has_section(name):
      raise NoSuchSection(name)
    return SectionView(self, name)

  def has_section(self, name):
    if self._parser.has_section(name):
      return True
    return name in self.defaults

  def registry(self, name):
    reg = 'registry:' + name
    if not self.has_section(reg):
      raise NoSuchSection(reg)
    return SectionView(self, name, reg)

  def registries(self):
    result = []
    default_found = False
    for section in self._parser.sections():
      if section.startswith('registry:'):
        name = section[9:]
        view = self.registry(name)
        if name == 'default':
          default_found = True
        result.append(view)
    if not default_found:
      result.insert(0, self.registry('default'))
    return result


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


filename = os.getenv('NPPM_CONFIG', NPPM_CONFIG)
filename = os.path.normpath(os.path.expanduser(filename))

config = Config(filename, {
  '__global__': {
    'author': getpass.getuser(),
    'license': 'MIT'
  },
  'registry:default': {
    'url': 'https://registry.nodepy.org'
  }
})

exports = config
