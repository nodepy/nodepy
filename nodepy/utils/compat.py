"""
Small Python 2/3 compatibility layer.
"""

import sys


def as_text(x, encoding=None):
  """
  Accepts a binary or unicode string and returns a unicode string. If *x* is
  not a string type, a #TypeError is raised.
  """

  if not isinstance(x, string_types):
    raise TypeError('expected string, got {} instead'.format(type(x).__name__))
  if not isinstance(x, text_type):
    x = x.decode(encoding or sys.getdefaultencoding())
  return x


if sys.version_info[0] == 3:
  PY2 = False
  PY3 = True
  text_type = str
  string_types = (str,)

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
  PY2 = True
  PY3 = False
  text_type = unicode
  string_types = (str, unicode)

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
