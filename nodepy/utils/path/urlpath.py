"""
A #pathlib.Path implementation for URLs.
"""

from nodepy.utils import pathlib
import os
import io
import posixpath
import six

try:
  from urllib.request import urlopen
  from urllib.parse import urlparse, urlunparse
except ImportError:
  from urllib2 import urlopen
  from urlparse import urlparse, urlunparse


class _UrlFlavour(pathlib._PosixFlavour):
  sep = '/'
  altsep = ''
  has_drv = False
  pathmod = posixpath
  is_supported = True

  def splitroot(self, part, sep=sep):
    res = urlparse(part)
    return (
      res.scheme + '://' if res.scheme else '',
      res.netloc + '/' if res.netloc else '',
      urlunparse(('', '', res.path, res.params, res.query, res.fragment))
    )


class PureUrlPath(pathlib.PurePath):
  _flavour = _UrlFlavour()
  __slots__ = ()


  def absolute(self):
    return self

  def is_absolute(self):
    return True


class UrlPath(pathlib.Path, PureUrlPath):
  __slots__ = ()

  # Wrapper for the socket._fileobject returned from #urlopen().
  # Necessary in Python 2 because socket._fileobject does not support
  # readable(), writable() and seekable(), and without this protocol it
  # can not be wrapped in #io.BufferedReader or #io.TextIOWrapper.
  class _readable(object):
    def __init__(self, fp, seekable=False):
      self._fp = fp
      self._seekable = seekable
      self._closed = False
    def __getattr__(self, name):
      return getattr(self._fp, name)
    def readable(self):
      return True
    def writable(self):
      return False
    def seekable(self):
      return self._seekable

  def owner(self):
    raise NotImplementedError("Path.owner() is unsupported for URLs")

  def group(self):
    raise NotImplementedError("Path.group() is unsupported for URLs")

  def open(self, flags='r', mode=0o666):
    if set(flags).difference('rbt'):
      raise IOError('URLs can be opened in read-mode only.')
    if six.PY2:
      fp = self._readable(urlopen(str(self)).fp)
    else:
      fp = urlopen(str(self))
    if not isinstance(fp, io.BufferedReader):
      fp = io.BufferedReader(fp)
    if 'b' not in flags:
      fp = io.TextIOWrapper(fp)
    return fp

  def is_dir(self):
    return False

  def is_file(self):
    return True

  def exists(self):
    return True

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

  def is_directory_listing_supported(self):
    return False

  def resolve(self):
    return self


def make(s, pure=False):
  """
  Maker for the #UrlPath.
  """

  res = urlparse(s)
  if res.scheme and res.netloc:
    return PureUrlPath(s) if pure else UrlPath(s)
  raise ValueError('not a URL: {!r}'.format(s))
