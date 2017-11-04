"""
A #pathlib.Path implementation for URLs.
"""

from nodepy.utils import pathlib
import os
import io
import posixpath

try:
  from urllib.request import urlopen
  from urllib.parse import urlparse, urlunparse
except ImportError:
  from urllib2 import urlopen, urlparse, urlunparse


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


class UrlPath(pathlib.Path, PureUrlPath):
  __slots__ = ()

  def owner(self):
    raise NotImplementedError("Path.owner() is unsupported for URLs")

  def group(self):
    raise NotImplementedError("Path.group() is unsupported for URLs")

  def open(self, flags='r', mode=0o666):
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
