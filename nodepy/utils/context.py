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
