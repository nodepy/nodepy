"""
Implements the #StdResolver that is the default resolver when creating a
non-bare context. It operates on the filesystem using the #pathlib module.
"""

from nodepy import base, utils
from nodepy.utils import json, pathlib
import itertools
import os
import warnings


def load_package(context, directory, doraise_exists=True):
  """
  Loads a #base.Package from the specified *directory* in TOML format.
  """

  if not isinstance(directory, pathlib.Path):
    directory = pathlib.Path(directory)
  if not utils.path.is_directory_listing_supported(directory):
    return None

  filename = directory.joinpath(context.package_manifest)
  if not doraise_exists and not filename.is_file():
    return None
  with filename.open('r') as fp:
    payload = json.load(fp)
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

  @staticmethod
  def resolve_link(context, path):
    """
    Checks if there exists a package-link file somewhere in the parent
    directories of *path* and returns an update path pointing to the linked
    location.
    """

    if not utils.path.is_directory_listing_supported(path):
      return path

    link_suffix = context.link_suffix
    for curr in utils.path.upiter(path):
      if not curr.name: break  # probably root of the filesystem
      lnk = curr.with_name(curr.name + link_suffix)
      if lnk.exists():
        with lnk.open() as fp:
          package_dir = pathlib.Path(fp.readline().strip())
          if package_dir.exists():
            path = package_dir.joinpath(path.relative_to(curr))
            path = context.augment_path(path)
            break
          else:
            msg = 'Broken link file "{}" --> "{}"'.format(lnk, package_dir)
            warnings.warn(msg, ImportWarning)
    return path

  def __try_load(self, paths, request):
    """
    Attempts to load determine the filename, package and loader for the
    specified *request*, to be loaded from the specified *paths*, and
    returns a tuple of (package, loader, path). If the request can not
    be resolved, (None, None, None) is returned.
    """

    def confront_loaders(path, package):
      for loader in self.loaders:
        if path.exists() and loader.can_load(request.context, path):
          return package, loader, path
        for suggestion in loader.suggest_files(request.context, path):
          if suggestion.exists():
            return package, loader, suggestion
      return None

    if request.string.is_absolute():
      path = self.resolve_link(request.context, request.string.path())
      package = self.find_package(request.context, path)
      return confront_loaders(path, package) or (None, None, None)

    for path in paths:
      filename = request.string.joinwith(path)
      filename = request.context.augment_path(filename)
      filename = self.resolve_link(request.context, filename)

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

      filename = filename.absolute()

      # Package.main is regarded independent from Package.resolve_root.
      if is_package_root:
        filename = filename.joinpath(package.main)
      elif package and package.resolve_root and not request.string.is_relative():
        rel = filename.relative_to(package.directory)
        filename = package.directory.joinpath(package.resolve_root, rel)

      result = confront_loaders(filename, package)
      if not result and is_package_root and not package.is_main_defined:
        result = confront_loaders(package.directory, package)
      if result is not None:
        return result

    return None, None, None

  def package_for_directory(self, context, path):
    path = path.absolute().resolve(strict=False)
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
    if request.string.is_relative():
      paths = [request.directory]
    elif request.string.is_absolute():
      paths = []
    else:
      paths = itertools.chain(request.related_paths, self.paths)
      paths = itertools.chain(paths, request.additional_search_path)
      paths = list(paths)

    package, loader, filename = self.__try_load(paths, request)
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

    def suggest_files(self, context, path):
      raise NotImplementedError

    def can_load(self, context, path):
      raise NotImplementedError

    def load_modules(self, context, package, filename):
      raise NotImplementedError
