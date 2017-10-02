"""
A void implementation of #pathlib.Path.
"""

from nodepy.utils import pathlib


class _NoPathFlavour(pathlib._Flavour):
  sep = '/'
  altsep = ''
  has_drv = False
  pathmod = None
  is_supported = True

  def splitroot(self, path, sep=sep):
    return '', '', path


class PureNoPath(pathlib.PurePath):
  _flavour = _NoPathFlavour()
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
    raise NotImplementedError("can not join PureNoPath")

  def with_name(self, name):
    return type(self)(name)

  def with_suffix(self, suffix):
    raise NotImplementedError('PureNoPath.with_suffix() is not supported')


class NoPath(pathlib.Path, PureNoPath):
  __slots__ = ()

  def owner(self):
    raise NotImplementedError("NoPath.owner() is not unsupported")

  def group(self):
    raise NotImplementedError("NoPath.group() is not unsupported")

  def open(self, flags='r', mode=0o666):
    raise NotImplementedError("NoPath.open() not supported")
    if set(flags).difference('rbt'):
      raise IOError('URLs can be opened in read-mode only.')
    request = urlopen(str(self))
    return (io.BufferedReader if 'b' in flags else io.TextIOWrapper)(request)

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
