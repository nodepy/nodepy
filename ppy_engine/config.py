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

__all__ = ['get_default_prefix', 'Config']

import appdirs
import collections
import os
import sys


def is_virtualenv():
  return hasattr(sys, 'real_prefix') or (sys.prefix == sys.base_prefix)


def get_default_prefix():
  """
  Returns the default prefix path of where to store ppy packages, Python
  modules, scripts, etc.
  """

  if is_virtualenv():
    # Use the virtualenv's prefix instead.
    return os.path.join(sys.prefix, 'share', 'ppy')

  return appdirs.user_data_dir('ppy', False, roaming=True)


class Config(object):
  """
  Reader/writer for the ppy configuration file. The file format must be in
  plain `key=value` format, one per line.

  # Parameters
  filename (str): The config file to parse, and optionally save to. Pass
      #NotImplemented to prevent the #Config object from actually loading any
      configuration file. Defaults to the value of the `PPY_CONFIG` environment
      variable or `~/.ppyrc`.
  """

  defaults = {
    'prefix': get_default_prefix()
  }

  def __init__(self, filename=NotImplemented, defaults=None):
    if filename is NotImplemented:
      filename = os.getenv('PPY_CONFIG', '~/.ppyrc')
    if filename:
      filename = os.path.normpath(os.path.expanduser(filename))
    if defaults is None:
      defaults = Config.defaults

    self.filename = filename
    self.values = collections.OrderedDict()
    self.defaults = defaults
    self.loaded = False
    if self.filename:
      self.load()

  def __repr__(self):
    return '<Config {!r}>'.format(self.filename)

  def load(self):
    self.loaded = False
    if not os.path.isfile(self.filename):
      return
    self.loaded = True
    with open(self.filename, 'r') as fp:
      for line in fp:
        key, value = line.rstrip('\n').partition('=', '')
        self.values[key.lower()] = value or ''

  def save(self, create_directory=True):
    if not self.values:
      return
    if create_directory:
      dirname = os.path.dirname(self.filename)
      if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(self.filename, 'w') as fp:
      for key, value in self.values.items():
        fp.write('{}={}\n'.format(key, value))

  def __getitem__(self, key):
    try:
      return self.values[key]
    except KeyError:
      return self.defaults[key]

  def __setitem__(self, key, value):
    self.values[key] = str(value)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default
