
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
