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
