"""
Concrete implementation of the Node.py runtime.
"""

from nodepy import base, loader, resolver
from nodepy.utils import pathlib


class Require(object):
  """
  Implements the `require` object that is available to Node.py modules.
  """

  def __init__(self, context, directory):
    assert isinstance(context, Context)
    assert isinstance(directory, pathlib.Path)
    self.context = context
    self.directory = directory
    self.cache = {}

  def __call__(self, request):
    module = self.resolve(request)
    if not module.loaded:
      module.load()
    if module.exports is NotImplemented:
      return module.namespace
    return module.exports

  def resolve(self, request):
    return self.context.resolve(request, self.directory)

  @property
  def main(self):
    return self.context.main_module


class Context(object):

  modules_directory_name = '.nodepy/modules'

  def __init__(self, bare=False):
    self.resolvers = []
    self.modules = {}
    self.main_module = None
    if not bare:
      std_resolver = resolver.StdResolver([], [loader.PythonLoader()])
      self.resolvers.append(std_resolver)

  def resolve(self, request, directory=None):
    if not isinstance(request, base.Request):
      if directory is None:
        directory = pathlib.Path.cwd()
      request = base.Request(self, directory, request)

    search_paths = []
    for resolver in self.resolvers:
      try:
        module = resolver.resolve_module(request)
      except base.ResolveError as exc:
        assert exc.request is request, (exc.request, request)
        search_paths.extend(exc.search_paths)
        continue

      if not isinstance(module, base.Module):
        msg = '{!r} returned non-Module object {!r}'
        msg = msg.format(type(resolver).__name__, type(module).__name__)
        raise RuntimeError(msg)
      have_module = self.modules.get(module.filename)
      if have_module is not None and have_module is not module:
        msg = '{!r} returned new Module object besides an existing entry '\
              'in the cache'.format(type(resolver).__name__)
        raise RuntimeError(msg)
      self.modules[module.filename] = module
      return module

    raise base.ResolveError(request, search_paths)
