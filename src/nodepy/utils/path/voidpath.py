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
A void implementation of #pathlib.Path.
"""

import pathlib2 as pathlib


class _VoidPathFlavour(pathlib._Flavour):
  sep = '/'
  altsep = ''
  has_drv = False
  pathmod = None
  is_supported = True

  def splitroot(self, path, sep=sep):
    return '', '', path


class PureVoidPath(pathlib.PurePath):
  _flavour = _VoidPathFlavour()
  __slots__ = ()

  drive = ''
  root = ''
  anchor = ''
  suffix = ''
  suffixes = ()
  parents = ()

  @property
  def parent(self):
    return self

  def joinpath(self, *args):
    raise NotImplementedError("can not join PureVoidPath")

  def with_name(self, name):
    return type(self)(name)

  def with_suffix(self, suffix):
    raise NotImplementedError('PureVoidPath.with_suffix() is not supported')

  def is_absolute(self):
    return True


class VoidPath(pathlib.Path, PureVoidPath):
  __slots__ = ()

  def owner(self):
    raise NotImplementedError("VoidPath.owner() is not unsupported")

  def group(self):
    raise NotImplementedError("VoidPath.group() is not unsupported")

  def open(self, flags='r', mode=0o666):
    raise NotImplementedError("VoidPath.open() not supported")

  def exists(self):
    False

  def is_dir(self):
    return False

  def is_file(self):
    return False

  def is_symlink(self):
    return False

  def is_socket(self):
    return False

  def is_fifo(self):
    return False

  def is_char_device(self):
    return False

  def is_block_device(self):
    return False
