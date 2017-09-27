"""
Concrete implementation of the Node.py runtime.
"""

from nodepy import base
from nodepy.utils import pathlib, pathutils
import itertools


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

  def resolve(self, request):
    return self.context.resolve(request, self.directory)

  def __call__(self, request):
    module = self.resolve(request)
    if not module.loaded:
      module.load()
    if module.exports is NotImplemented:
      return module.namespace
    return module.exports


class Context(object):

  modules_directory_name = '.nodepy/modules'

  def __init__(self, bare=False):
    self.resolvers = []
    self.modules = {}
    if not bare:
      resolver = FsResolver([])
      resolver.loaders.append(PythonLoader())
      self.resolvers.append(resolver)

  def resolve(self, request, directory=None):
    if not isinstance(request, base.Request):
      if directory is None:
        directory = pathlib.Path.cwd()
      request = base.Request(self, directory, request)

    for resolver in self.resolvers:
      # TODO: Catch possible #ResolveError and re-raise if no resolver matched.
      return resolver.resolve_module(request)


class FsResolver(base.Resolver):
  """
  The standard resolver that works on the filesystem (or whatever the PathLike
  objects are implemented for).
  """

  def __init__(self, paths):
    assert all(isinstance(x, pathlib.Path) for x in paths)
    self.paths = paths
    self.loaders = []

  def _ask_loaders(self, paths, request):
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

    loader, filename = self._ask_loaders(paths, request)
    if not loader:
      raise base.ResolveError(request, paths)

    return loader.load_module(request.context, filename)


class PythonLoader(base.Loader):

  class PythonModule(base.Module):
    def load(self):
      self.init()
      self.loaded = True
      with self.filename.open('r') as fp:
        code = compile(fp.read(), str(self.filename), 'exec', dont_inherit=True)
      exec(code, vars(self.namespace))

  def suggest_files(self, path):
    return [path.with_suffix('.py')]

  def load_module(self, context, filename):
    return self.PythonModule(context, None, filename)
