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
    self.context.load_module(module)
    if module.exports is NotImplemented:
      return module.namespace
    return module.exports

  def resolve(self, request):
    return self.context.resolve(request, self.directory)

  @property
  def main(self):
    return self.context.main_module

  @property
  def current(self):
    return self.context.current_module


class Context(object):

  modules_directory_name = '.nodepy/modules'

  def __init__(self, bare=False):
    self.resolvers = []
    self.modules = {}
    self.module_stack = []
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

  def load_module(self, module, remove_on_error=True):
    """
    This method should be the preferred way to call #Module.load() as it
    performs integrity checks and keeps track of the module in the
    #Context.module_stack list.

    If an exception occurs while the module is executed, it is removed from
    the #Context.modules cache as it is assumed to have an invalid state.
    """

    if module.loaded:
      return

    self.module_stack.append(module)
    try:
      module.load()
    except:
      self.modules.pop(module.filename, None)
      raise
    finally:
      if self.module_stack.pop() is not module:
        raise RuntimeError('Context.module_stack corrupted')

  @property
  def current_module(self):
    if self.module_stack:
      return self.module_stack[-1]
    return None
