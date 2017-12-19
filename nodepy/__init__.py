"""
The Node.py runtime provides an alternative to standard Python modules
similar to Node.js.
"""

__version__ = '2.0.1'
__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'

from . import context, runtime
import pathlib2 as pathlib
import atexit

_default_context = None
_default_context_enter = None
_require_cache = {}


def get_default_context():
  global _default_context
  if not _default_context:
    _default_context = context.Context()
  return _default_context


def require(*args, **kwargs):
  """
  Enters the default context (as returned by #get_ddefault_context())
  and registers the exit function with #atexit.register(). The returns the
  result of the default context's `require()` with the specified arguments,
  or alternatively the result of a require at the specified *directory*
  (keyword argument only).

  IMPORTANT: This function should only be used for one-off aplications
  that would never create multiple Node.py contexts.
  """

  ctx = get_default_context()

  global _default_context_enter
  if not _default_context_enter:
    _default_context_enter = ctx.enter()
    _default_context_enter.__enter__()
    atexit.register(_default_context_enter.__exit__, None, None, None)

  directory = kwargs.pop('directory', None)
  if directory is not None:
    if isinstance(directory, str):
      directory = pathlib.Path(directory)
    require = _require_cache.get(directory)
    if not require:
      require = context.Require(ctx, directory)
      _require_cache[directory] = require
  else:
    require = ctx.require

  return require(*args, **kwargs)
