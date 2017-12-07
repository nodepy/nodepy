"""
A #pathlib.Path implementation for ZIP files.
"""

from . import _core as path
import codecs
import errno
import functools
import pathlib2 as pathlib
import posixpath
import six
import sys
import zipfile

# XXX Find a way to close all these zip files when appropriate.
open_zipfiles = {}


if six.PY2:
  def _error_factory(name, eno):
    def func(msg):
      return OSError(eno, str(eno), msg)
    func.__name__ = func.__qualname__ = name
    return func
  FileNotFoundError = _error_factory('FileNotFoundError', errno.ENOENT)
  NotADirectoryError = _error_factory('NotADirectoryError', errno.ENOTDIR)
  PermissionError = _error_factory('PermissionError', errno.EPERM)


class maybe_classmethod(object):

  def __init__(self, func):
    functools.update_wrapper(self, func)
    self.__wrapped__ = func

  def __get__(self, obj, type=None):
    if obj is not None:
      return functools.partial(self.__wrapped__, obj)
    elif type is not None:
      return functools.partial(self.__wrapped__, type)
    raise RuntimeError


class CopyFromSourceMixin(object):

  # This used to be a classmethod on #pathlib.PurePath.
  # You win some, you loose some.
  @maybe_classmethod
  def _from_parsed_parts(self, *args, **kwargs):
    new = super(CopyFromSourceMixin, self)._from_parsed_parts(*args, **kwargs)
    if not isinstance(self, type):
      new._copy_from_source(self)
    return new

  @maybe_classmethod
  def _from_parts(self, *args, **kwargs):
    new = super(CopyFromSourceMixin, self)._from_parts(*args, **kwargs)
    if not isinstance(self, type):
      new._copy_from_source(self)
    return new

  @property
  def parents(self):
    parents = pathlib._PathParents(self)
    parents._pathcls = self
    return parents


class PureZipPath(CopyFromSourceMixin, pathlib.PurePath):
  _flavour = pathlib._PosixFlavour()
  _flavour.is_supported = True
  __slots__ = ()

  def __new__(cls, zipf, s):
    self = super(PureZipPath, cls).__new__(cls, s)
    self._init_zipf(zipf)
    return self

  def _copy_from_source(self, source):
    self._init_zipf(source._zipf)

  def _init_zipf(self, zipf):
    self._zipf = zipf


class ZipPath(pathlib.Path, PureZipPath):

  def __new__(cls, zipf, s):
    self = super(ZipPath, cls).__new__(cls, '/' + s.strip('/'))
    self._init_zipf(zipf)
    return self

  def _init_zipf(self, zipf):
    self._zipf = zipf
    self._namelist = zipf.namelist()
    self._info = NotImplemented

  def _get_zipinfo(self):
    if self._info is not NotImplemented:
      return self._info
    name = posixpath.normpath(str(self)).strip('/')
    try:
      self._info = self._zipf.getinfo(name)
    except KeyError:
      try:
        self._info = self._zipf.getinfo(name + '/')
      except KeyError:
        self._info = None
    return self._info

  def exists(self):
    if str(self) == '/': return True
    return self._get_zipinfo() is not None

  def is_dir(self):
    if str(self) == '/': return True
    info = self._get_zipinfo()
    if info:
      return info.filename.endswith('/')
    return False

  def is_file(self):
    info = self._get_zipinfo()
    if info:
      return not info.filename.endswith('/')
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

  def resolve(self, strict=False):
    return self

  def iterdir(self):
    if str(self) == '/':
      for name in self._namelist:
        if name.rstrip('/').count('/') == 0:
          yield type(self)(self._zipf, name)
    else:
      if not self.exists():
        raise FileNotFoundError('ZipFile does not contain: ' + str(self))
      if not self.is_dir():
        raise NotADirectoryError('ZipFile, item not a directory: ' + str(self))
      filename = self._info.filename
      for name in self._namelist:
        if name.startswith(filename) and name.find('/', len(filename)) < 0:
          yield type(self)(self._zipf, name)

  def open(self, flags='r', mode=0o666):
    if 'b' in flags:
      binary = True
      flags = flags.replace('b', '')
    else:
      binary = False
    if not self.exists():
      raise FileNotFoundError('ZipFile item does not exist: ' + str(self))
    if not self.is_file():
      raise PermissionError('Permission denied: ' + str(self))
    fp = self._zipf.open(self._info, flags)
    if not binary:
      fp = codecs.getreader(sys.getdefaultencoding())(fp)
    return fp

  def absolute(self):
    new = super(ZipPath, self).absolute()
    return type(self)(self._zipf, posixpath.normpath(str(new)))


def make(s, pure=False):
  """
  Accepts a string or a #pathlib.Path instance and converts it to a #ZipPath
  or #PureZipPath if *s* is a path pointing to a ZIP file or any of its parent
  path elements.
  """

  if isinstance(s, six.string_types):
    s = pathlib.Path(s)
  if isinstance(s, pathlib.Path) and path.is_directory_listing_supported(s):
    for current in path.upiter(s):
      if current in open_zipfiles:
        zipf = open_zipfiles[current]
      elif not current.is_file(): continue
      else:
        fp = current.open('rb')
        if not zipfile.is_zipfile(fp):
          fp.close()
          continue
        zipf = zipfile.ZipFile(fp, 'r')
        open_zipfiles[current] = zipf
      relname = s.relative_to(current)
      relname = '/'.join(reversed([x.name for x in path.upiter(relname)]))
      return ZipPath(zipf, relname)
  raise ValueError('can not create ZipPath: {!r}'.format(s))
