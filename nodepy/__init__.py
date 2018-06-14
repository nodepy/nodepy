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
The Node.py runtime provides an alternative to standard Python modules
similar to Node.js.
"""

__version__ = '2.1.1'
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
