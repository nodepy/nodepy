"""
Implements the #StdResolver that is the default resolver when creating a
non-bare context. It operates on the filesystem using the #pathlib module.
"""

from nodepy import base, utils
from nodepy.utils import pathlib
from nodepy.vendor import toml
import itertools


def load_package(context, directory, doraise_exists=True):
  """
  Loads a #base.Package from the specified *directory* in TOML format.
  """

  if not isinstance(directory, pathlib.Path):
    directory = pathlib.Path(directory)
  filename = directory.joinpath(context.package_manifest)
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
    link_file = request.context.link_file
    for path in paths:
      filename = path.joinpath(request.string)

      # Check if somewhere in that path there is a link file.
      for lnk in (x.joinpath(link_file) for x in utils.path.upiter(filename)):
        if lnk.exists():
          with lnk.open() as fp:
            package_dir = pathlib.Path(fp.readline().strip())
            # TODO: Raise a resolve error immediately if the linked
            # directory does not exist?
            # if not package_dir.is_dir():
            filename = package_dir.joinpath(filename.relative_to(lnk.parent))

      package = None
      is_package_root = False

      # Check if the request aims for a top-level package.
      is_dir = filename.is_dir()
      if is_dir:
        package = self.package_for_directory(request.context, filename)
      if is_dir and package is not None:
        is_package_root = True
      else:
        package = self.find_package(request.context, filename)

      # Package.main is regarded independent from Package.resolve_root.
      if is_package_root:
        filename = filename.joinpath(package.main)
      elif package and package.resolve_root:
        filename = package.directory.joinpath(package.resolve_root)

      # Check every registered loader if they can load the path or suggest
      # other paths from it.
      for loader in self.loaders:
        if filename.exists() and loader.can_load(filename):
          return package, loader, filename
        for suggestion in loader.suggest_files(filename):
          if suggestion.exists():
            return package, loader, suggestion

    return None, None, None

  def package_for_directory(self, context, path):
    path = path.resolve()
    package = context.packages.get(path)
    if package is None:
      package = load_package(context, path, doraise_exists=False)
      if package is not None:
        context.packages[path] = package
    return package

  def find_package(self, context, path):
    for path in utils.path.upiter(path):
      package = self.package_for_directory(context, path)
      if package is not None:
        return package
    return None

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
