"""
Concrete implementation of the Node.py runtime.
"""

from nodepy import base, extensions, loader, resolver, utils
from nodepy.utils import pathlib
import contextlib
import localimport
import sys


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

  def __call__(self, request, exports=True):
    assert isinstance(request, str)
    module = self.cache.get(request)
    if module and not module.exception:
      return module
    module = self.resolve(request)
    self.context.load_module(module)
    self.cache[request] = module
    if exports:
      if module.exports is NotImplemented:
        return module.namespace
      return module.exports
    else:
      return module

  def resolve(self, request):
    return self.context.resolve(request, self.directory)

  def star(self, request, symbols=None):
    """
    Performs a 'star' import into the parent frame.
    """

    if isinstance(symbols, str):
      if ',' in symbols:
        symbols = [x.strip() for x in symbols.split(',')]
      else:
        symbols = symbols.split()

    into = sys._getframe(1).f_locals
    namespace = self(request)

    if symbols is None:
      symbols = getattr(namespace, '__all__', None)
    if symbols is None:
      for key in dir(namespace):
        if not key.startswith('_') and key not in ('module', 'require'):
          into[key] = getattr(namespace, key)
    else:
      for key in symbols:
        into[key] = getattr(namespace, key)

  @property
  def main(self):
    return self.context.main_module

  @property
  def current(self):
    return self.context.current_module


class Context(object):

  modules_directory = '.nodepy_modules'
  package_manifest = 'nodepy-package.toml'
  package_main = 'index'
  link_file = '.nodepy-link.txt'

  def __init__(self, bare=False):
    self.extensions = []
    self.resolvers = []
    self.modules = {}
    self.packages = {}
    self.module_stack = []
    self.main_module = None
    self.localimport = localimport.localimport([])
    if not bare:
      loaders = [loader.PythonLoader(), loader.PackageRootLoader()]
      std_resolver = resolver.StdResolver([], loaders)
      self.resolvers.append(std_resolver)
      self.extensions.append(extensions.ImportSyntax())

  @contextlib.contextmanager
  def enter(self, isolated=False):
    """
    Returns a context-manager that enters and leaves this context. If
    *isolated* is #True, the #localimport module will be used to restore
    the previous global importer state when the context is exited.

    > Note: This method reloads the #pkg_resources module on entering and
    > exiting the context. This is necessary to update the state of the
    > module for the updated global importer state.
    """

    @contextlib.contextmanager
    def reload_pkg_resources():
      utils.machinery.reload_pkg_resources()
      yield
      if isolated:
        utils.machinery.reload_pkg_resources()

    @contextlib.contextmanager
    def activate_localimport():
      self.localimport.__enter__()
      yield
      if isolated:
        self.localimport.__exit__()

    with utils.context.ExitStack() as stack:
      stack.add(activate_localimport())
      stack.add(reload_pkg_resources())
      sys.path_importer_cache.clear()
      yield

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

  def load_module(self, module, do_init=True):
    """
    This method should be the preferred way to call #Module.load() as it
    performs integrity checks and keeps track of the module in the
    #Context.module_stack list.

    If loading the module resulted in an exception before and it is still
    stored in #Module.exception, it is re-raised.
    """

    assert isinstance(module, base.Module)
    if module.exception:
      utils.compat.reraise(*module.exception)
    if module.loaded:
      return
    if module.filename not in self.modules:
      msg = '{!r} can not be loaded when not in Context.modules'
      raise RuntimeError(msg.format(module))

    if do_init:
      module.init()
    self.module_stack.append(module)
    try:
      module.load()
    except:
      module.exception = sys.exc_info()
      del self.modules[module.filename]
      raise
    else:
      module.loaded = True
    finally:
      if self.module_stack.pop() is not module:
        raise RuntimeError('Context.module_stack corrupted')

  @property
  def current_module(self):
    if self.module_stack:
      return self.module_stack[-1]
    return None
