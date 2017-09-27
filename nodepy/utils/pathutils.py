
from nodepy.utils import pathlib


def parts(path):
  name = path.name
  if name:
    yield name
  for path in path.parents:
    yield path.name


def upiter(path):
  prev = path
  while prev != path:
    yield path
    prev, path = path, path.parent


def endswith(path, ending):
  if not isinstance(ending, pathlib.Path):
    ending = pathlib.Path(ending)
  for part in parts(ending):
    if not part:
      continue
    if part != path.name:
      return False
    path = path.parent
  return True
