"""
Implements the #StdResolver that is the default resolver when creating a
non-bare context. It operates on the filesystem using the #pathlib module.
"""

from nodepy import base
from nodepy.utils import pathlib, pathutils
import itertools
import toml


def load_package(context, directory, doraise_exists=True):
  """
  Loads a #base.Package from the specified *directory* in TOML format.
  """

  if not isinstance(directory, pathlib.Path):
    directory = pathlib.Path(directory)
  filename = directory.joinpath(context.metadata_filename)
  if not doraise_exists and not filename.is_file():
    return None
  with filename.open('r') as fp:
    payload = toml.load(fp)
  return base.Package(context, directory, payload)


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
      # Check if the request aims for a top-level package directory.
      package = None
      is_toplevel = False
      if path.is_dir():
        package = self.package_for_directory(request.context, path)
        if package:
          path = path.joinpath(package.main or context.package_main_default)
          is_toplevel = True

      # Check every registered loader if they can load the path or suggest
      # other paths from it.
      for loader in self.loaders:
        if loader.can_load(path):
          return package, loader, path
        for filename in loader.suggest_files(path):
          if filename.exists():
            return package, loader, filename

    return None, False, None, None

  def package_for_directory(self, context, path):
    path = path.resolve()
    package = context.packages.get(path)
    if package is None:
      package = load_package(context, path, doraise_exists=False)
      if package is not None:
        context.packages[path] = package
    return package

  def resolve_module(self, request):
    if request.is_relative():
      paths = [request.directory]
    else:
      paths = list(itertools.chain(request.related_paths, self.paths))

    package, loader, filename = self.__ask_loaders(paths, request)
    if not loader:
      raise base.ResolveError(request, paths)

    filename = filename.resolve()
    module = request.context.modules.get(filename)
    if not module:
      module = loader.load_module(request.context, package, filename)
    return module

  class Loader(object):
    """
    Interface for suggesting files to load from a request. Implementations of
    this interface are added to the #StdResolver to "configure" it.
    """

    def suggest_files(self, path):
      raise NotImplementedError

    def can_load(self, path):
      raise NotImplementedError

    def load_modules(self, request, package, filename):
      raise NotImplementedError
