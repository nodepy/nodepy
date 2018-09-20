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

import functools
import threading

_finally_local = threading.local()

def finally_(push_func=None):
  """
  This decorator creates a new list for every call to the decorated function.
  Calling this function from inside the decorated function will push the
  *push_func* argument onto this newly created list. When the function returns
  or raises an exception, all items in this list are called.

  # Example

  ```python
  @finally_()
  def some_function():
    # ... do setup
    finally_(do_cleanup)
    # ... do stuff
  ```
  """

  if push_func is not None:
    _finally_local.stack[-1].append(push_func)
  else:
    def decorator(func):
      @functools.wraps(func)
      def wrapper(*args, **kwargs):
        if not hasattr(_finally_local, 'stack'):
          _finally_local.stack = []
        _finally_local.stack.append([])
        try:
          return func(*args, **kwargs)
        finally:
          for cleanup in _finally_local.stack.pop():
            cleanup()
      return wrapper
    return decorator
