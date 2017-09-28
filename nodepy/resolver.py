"""
Implements the #StdResolver that is the default resolver when creating a
non-bare context. It operates on the filesystem using the #pathlib module.
"""

from nodepy import base
from nodepy.utils import pathlib
import itertools


class StdResolver(base.Resolver):
  """
  The standard resolver implementation.
  """

  def __init__(self, paths, loaders):
    assert all(isinstance(x, pathlib.Path) for x in paths)
    assert all(isinstance(x, StdResolver.Loader) for x in loaders)
    self.paths = paths
    self.loaders = loaders

  def __ask_loaders(self, paths, request):
    for path in (x.joinpath(request.string) for x in paths):
      for loader in self.loaders:
        for filename in loader.suggest_files(path):
          if filename.exists():
            return loader, filename
    return None, None

  def resolve_module(self, request):
    if request.is_relative():
      paths = [request.directory]
    else:
      paths = list(itertools.chain(request.related_paths, self.paths))

    loader, filename = self.__ask_loaders(paths, request)
    if not loader:
      raise base.ResolveError(request, paths)

    filename = filename.resolve()
    module = request.context.modules.get(filename)
    if module:
      return module

    return loader.load_module(request.context, filename)

  class Loader(object):
    """
    Interface for suggesting files to load from a request. Implementations of
    this interface are added to the #StdResolver to "configure" it.
    """

    def suggest_files(self, path):
      raise NotImplementedError

    def load_modules(self, request, filename):
      raise NotImplementedError
