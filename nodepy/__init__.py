"""
The Node.py runtime provides an alternative to standard Python modules
similar to Node.js.
"""

__version__ = '2.0.0-dev'
__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'

from . import context, runtime
from .utils import pathlib
import atexit

default_context = context.Context()
_default_context_enter = None
_require_cache = {}

def require(*args, **kwargs):
  """
  Enters the #default_context once and registers the exit function with
  #atexit.register(). The returns the result of #default_context.require().
  Optionally, the additional *directory* keyword argument can be passed. A
  separate #Require instance will be created for that directory.

  IMPORTANT: This function should only be used for one-off aplications
  that would never create multiple Node.py contexts.
  """

  global _default_context_enter
  if not _default_context_enter:
    _default_context_enter = default_context.enter()
    _default_context_enter.__enter__()
    atexit.register(_default_context_enter.__exit__, None, None, None)

  directory = kwargs.pop('directory', None)
  if directory is not None:
    if isinstance(directory, str):
      directory = pathlib.Path(directory)
    require = _require_cache.get(directory)
    if not require:
      require = context.Require(default_context, directory)
      _require_cache[directory] = require
  else:
    require = default_context.require

  return require(*args, **kwargs)
