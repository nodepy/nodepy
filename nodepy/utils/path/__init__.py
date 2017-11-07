
from nodepy.utils import pathlib
from .urlpath import PureUrlPath, UrlPath
from .voidpath import PureVoidPath, VoidPath


def lparts(path):
  """
  Yields the components of *path* from left to right.
  """

  return reversed(list(rparts(path)))


def rparts(path):
  """
  Yields the components of *path* from right to left.
  """

  # Yield from the back of the path.
  name = path.name
  if name:
    yield name
  for path in path.parents:
    yield path.name


def upiter(path):
  prev = None
  while prev != path:
    yield path
    prev, path = path, path.parent


def endswith(path, ending):
  if not isinstance(ending, pathlib.Path):
    ending = pathlib.Path(ending)
  for part in rparts(ending):
    if not part:
      continue
    if part != path.name:
      return False
    path = path.parent
  return True


def is_directory_listing_supported(path):
  """
  Returns #True if the specified *path* object support directory listing.
  """

  if hasattr(path, 'is_directory_listing_supported'):
    return path.is_directory_listing_supported()
  elif type(path) in (pathlib.Path, pathlib.WindowsPath, pathlib.PosixPath):
    return True
  else:
    raise TypeError('unsupported type: ' + type(path).__name__)


_makers = []


def register_maker(func):
  """
  Registers *func* as a function that is tested with #make(). The function
  must accept the same arguments as the #make() function and return a
  #pathlib.Path-like object or raise a #ValueError.
  """

  _makers.append(func)


def make(s, pure=False):
  """
  Given the string *s*, this function will test all functions in the #makers
  list to see if they can wrap the string in a #pathlib.Path-like object.
  Ultimately, if no maker matched, a #pathlib.Path is returned.
  """

  if not isinstance(s, str):
    raise TypeError('make() requires a string argument, got ' + type(s).__name__)

  for func in _makers:
    try:
      return func(s, pure)
    except ValueError:
      pass

  return pathlib.PurePath(s) if pure else pathlib.Path(s)


register_maker(urlpath.make)
