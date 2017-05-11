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

import appdirs
import errno
import os
import sys

get_python_install_type = require('./env').get_python_install_type

PPYM_CONFIG = '~/.ppymrc'


class Config(object):
  """
  Reader/writer for the PPYM configuration file. The file format must be in
  plain `key=value` format, one per line. Lines starting with a hash (`#`)
  will be ignored.

  # Parameters
  filename (str): The config file to parse, and optionally save to. Pass
      #NotImplemented to prevent the #Config object from actually loading any
      configuration file. Defaults to the value of the `PPYM_CONFIG` environment
      variable or `~/.ppymrc`.
  defaults (dict): A dictionary of default values.
  """

  def __init__(self, filename=NotImplemented, defaults=None):
    if filename is NotImplemented:
      filename = os.getenv('PPYM_CONFIG', PPYM_CONFIG)
    if filename:
      filename = os.path.normpath(os.path.expanduser(filename))
    if defaults is None:
      defaults = {}

    self.filename = filename
    self.defaults = defaults
    self._values = {}
    self._values_ordered = []

    if self.filename is not None:
      self.load()

  def __repr__(self):
    return '<Config {!r}>'.format(self.filename)

  def load(self, filename=None, ignore_not_exists=True):
    """
    Loads the configuration from the specified *filename*. Defaults to the
    *filename* specified when the #Config object was created.
    """

    if filename is None:
      if self.filename is None:
        raise ValueError('no filename specified')

    try:
      with open(self.filename, 'r') as fp:
        for line in fp:
          line = line.rstrip('\n')
          if line.startswith('#') or not line:
            self._values_ordered.append([None, line])
          else:
            key, value = line.rstrip('\n').partition('=')[::2]
            key = key.lower().strip()
            value = (value or '').strip()
            self._values[key] = value
            self._values_ordered.append([key, value])
    except (OSError, IOError) as exc:
      if exc.errno != errno.ENOENT or not ignore_not_exists:
        raise

  def save(self, filename=None, fileobj=None):
    """
    Saves the configuration to the specified *filename*. Defaults to the
    *filename* specified when the #Config object was created.
    """

    if filename is None and fileobj is None:
      if self.filename is None:
        raise ValueError('no filename specified')
      filename = self.filename

    if not self._values_ordered:
      return

    # Make sure the directory we write to exists.
    dirname = os.path.dirname(self.filename)
    if not os.path.isdir(dirname):
      os.makedirs(dirname)

    try:
      if fileobj is None:
        fileobj = open(filename, 'w')

      for key, value in self._values_ordered:
        if key is None:
          fileobj.write(value)
        else:
          fileobj.write('{}={}'.format(key, value))
        fileobj.write('\n')
    finally:
      if filename is not None:
        fileobj.close()

  def __getitem__(self, key):
    try:
      return self._values[key]
    except KeyError:
      return self.defaults[key]

  def __setitem__(self, key, value):
    self._values[key] = str(value)
    for item in self._values_ordered:
      if item[0] == key:
        item[1] = value
        break
    else:
      self._values_ordered.append([key, value])

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default


config = Config()

# The URL of the PPYM registry from which packages should be downloaded
# from and uploaded to.
config.defaults['registry'] = 'https://ppym.org'

exports = config
