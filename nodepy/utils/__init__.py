
import pathlib2 as pathlib
import six

# TODO: Temporary workaround, find another way to reference this function,
#       but don't modify the six module.
def as_text(x, encoding=None):
  """
  Accepts a binary or unicode string and returns a unicode string. If *x* is
  not a string type, a #TypeError is raised.
  """

  if not isinstance(x, six.string_types):
    raise TypeError('expected string, got {} instead'.format(type(x).__name__))
  if not isinstance(x, six.text_type):
    x = x.decode(encoding or sys.getdefaultencoding())
  return x

compat = six
compat.as_text = as_text
del as_text


from . import context, iter, machinery, path
from .nopath import PureNoPath, NoPath
from .urlpath import PureUrlPath, UrlPath
