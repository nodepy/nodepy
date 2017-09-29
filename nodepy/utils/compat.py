"""
Small Python 2/3 compatibility layer.
"""

import sys


if sys.version_info[0] == 3:

  exec_ = getattr(__import__('builtins'), 'exec')

  def reraise(tp, value, tb=None):
    if value is None:
      value = tp()
    if value.__traceback__ is not tb:
      raise value.with_traceback(tb)
    raise value

  def iteritems(d):
    return d.items()

else:

  def exec_(_code_, _globs_=None, _locs_=None):
    """Execute code in a namespace."""
    if _globs_ is None:
      frame = sys._getframe(1)
      _globs_ = frame.f_globals
      if _locs_ is None:
        _locs_ = frame.f_locals
      del frame
    elif _locs_ is None:
      _locs_ = _globs_
    exec("""exec _code_ in _globs_, _locs_""")

  exec_("def reraise(tp, value, tb=None):\n"
        "  raise tp, value, tb")

  def iteritems(d):
    return d.iteritems()
