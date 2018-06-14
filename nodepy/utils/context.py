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
Context-manager utilities.
"""

import traceback


class ExitStack(object):
  """
  A stack of context-managers. Note that exceptions that occurr inside a
  context-manager added to the stack are dumped to stdout and swallowed.

  TODO: Make #__exit__() chain exceptions raised by context-managers that
        had been added to the stack and not just dump and swallow them.
  """

  def __init__(self):
    self.contexts = []
    self.inside = False

  def add(self, ctx):
    if not self.inside:
      raise RuntimeError('can not use ExitStack.add() outside of context')
    obj = ctx.__enter__()
    self.contexts.append(ctx)
    return obj

  def __enter__(self):
    self.inside = True
    return self

  def __exit__(self, *args):
    self.inside = False
    result = None
    for ctx in reversed(self.contexts):
      try:
        if ctx.__exit__(*args) is True:
          args = (None, None, None)
          result = True
      except Exception:
        traceback.print_exc()
    return result
