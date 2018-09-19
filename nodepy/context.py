# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Concrete implementation of the Node.py runtime.
"""

from itertools import chain
from nodepy import base, extensions, loader, resolver, utils
from nodepy.utils import tracing
from nodepy.utils.config import Config
import contextlib
import localimport
import os
import pathlib2 as pathlib
import six
import sys


class Require(object):
  """
  Implements the `require` object that is available to Node.py modules.
  """

  ResolveError = base.ResolveError

  class TryResolveError(Exception):
    pass

  def __init__(self, context, directory):
    assert isinstance(context, Context)
    assert isinstance(directory, pathlib.Path)
    self.context = context
    self.directory = directory
    self.path = []
    self.cache = {}

  def __call__(self, request, exports=True):
    module = self.resolve(request)
    if not module.loaded:
      self.context.load_module(module)
    if exports:
      if module.exports is NotImplemented:
        return module.namespace
      return module.exports
    else:
      return module

  def resolve(self, request):
    request = utils.as_text(request)
    module = self.cache.get(request)
    if not module or module.exception:
      module = self.context.resolve(request, self.directory, self.path)
      self.cache[request] = module
    return module

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

  def try_(self, *requests, **kwargs):
    """
    Load every of the specified *requests* until the first can be required
    without error. Only if the requested module can not be found will the
    next module be tried. Any other exception that occurs while loading a
    module will not be caught.

    If none of the requests match, a #TryResolveError is raised.

    Additional keyword arguments are:

    * load (bool)
    * exports (bool)
    """

    load = kwargs.pop('load', True)
    exports = kwargs.pop('exports', True)
    for key in kwargs:
      raise TypeError('unexpected keyword argument: {}'.format(key))

    for request in requests:
      try:
        if load:
          return self(request, exports=exports)
        else:
          return self.resolve(request)
      except self.ResolveError as exc:
        if exc.request.string != request:
          raise

    raise self.TryResolveError(requests)

  @property
  def main(self):
    return self.context.main_module

  @property
  def current(self):
    return self.context.current_module

  def breakpoint(self, tb=None, stackdepth=0):
    """
    Enters the interactive debugger. If *tb* is specified, the debugger will
    be entered at the specified traceback. *tb* may also be the value #True
    in which case `sys.exc_info()[2]` is used as the traceback.

    The `NODEPY_BREAKPOINT` environment variable will be considered to
    determine the implementation of the debugger. If it is an empty string
    or unset, #Context.breakpoint() will be called. If it is `0`, the
    function will return `None` immediately without invoking a debugger.
    Otherwise, it must be a string that can be `require()`-ed from the
    current working directory. The loaded module's `breakpoint()` function
    will be called with *tb* as single parameter.
    """

    if tb is True:
      tb = sys.exc_info()[2]
      if not tb:
        raise RuntimeError('no current exception information')

    var = os.getenv('NODEPY_BREAKPOINT', '')
    if var == '0':
      return

    if var:
      self.context.require(var).breakpoint(tb, stackdepth+1)
    else:
      self.context.breakpoint(tb, stackdepth+1)

  def starttracing(self, tracer=None, daemon=True, options=None):
    """
    Starts a thread that allows you to trace the Python stack frames.

    If a tracer is already running, a #RuntimeError is raised. The tracer
    that is being used is determined from the `NODEPY_TRACING` environment
    variable. If `NODEPY_TRACIN=`, it is treated as if it was not set.
    Otherwise, the variable must contain a request that will be required using
    #Context.require() and it must provide a #starttracing() function that
    creates a tracer, starts and returns it.
    """

    if self.context.tracer:
      raise RuntimeError('a tracer is already running')

    if options is None:
      options = {}

    var = os.getenv('NODEPY_TRACING', '')
    if var == '0':
      return
    if tracer is None:
      tracer = var

    if isinstance(tracer, str):
      if tracer in ('http', ''):
        tracer = tracing.HttpServerTracer(host=options.get('host'), port=options.get('port'))
      elif tracer == 'file':
        tracer = tracing.HtmlFileTracer(fname=options.get('path'), interval=options.get('interval'))
      else:
        tracer = self.context.require(tracer).starttracing(daemon, options)
        if not isinstance(tracer, BaseThread):
          raise RuntimeError('"{}:starttracing()" did not return a '
            'tracing.BaseThread instance, got {} instead'
            .format(tracer, type(tracer).__name__))
        if not tracer.is_alive():
          raise RuntimeError('"{}:starttracing()" did not return a '
            'running tracer thread.')
    elif isinstance(tracer, tracing.BaseThread):
      pass
    else:
      raise TypeError('unexpected type for tracer: {}'.format(
        type(tracer).__name__))

    if not tracer.is_alive():
      tracer.daemon = daemon
      tracer.start()

    self.context.tracer = tracer

  def stoptracing(self, wait=True):
    """
    Stops the #Context.tracer if one exists.
    """

    if self.context.tracer:
      self.context.tracer.stop(wait)
      self.context.tracer = None

  def new(self, directory):
    """
    Creates a new #Require instance for the specified *directory*.
    """

    if isinstance(directory, str):
      directory = pathlib.Path(directory)
    return type(self)(self.context, directory)


class Context(object):
  """
  Members:
    config (Config): The Node.py configuration, read from the file
      `~/.nodepy/config` if no value was given on construction. The
      `NODEPY_CONFIG` environment variable can be used to alter the change
      the path of the configuration file.
    maindir (str):
    require (Require):
    extensions (List[base.Extension]):
    resolver (resolver.StdResolver):
    resolvers (List[base.Resolver]):
    pathaugmentors (List[base.PathAugmentor]):
    modules (Dict[pathlib.Path, base.Module]):
    packages (Dict[pathlib.Path, base.Package]):
    module_stack (List[base.Module]):
    localimport (localimport.localimport):
    tracer (Union[None, tracing.HtmlFileTracer, tracing.HttpServerTracer]):
  """

  modules_directory = '.nodepy/modules'
  pipprefix_directory = '.nodepy/pip'
  package_manifest = 'nodepy.json'
  package_main = 'index'
  link_suffix = '.nodepy-link'

  def __init__(self, maindir=None, config=None, parent=None, isolate=True, inherit=True):
    if not config and not parent:
      filename = os.path.expanduser(os.getenv('NODEPY_CONFIG', '~/.nodepy/config'))
      config = Config(filename, {})
    if not maindir and not parent:
      maindir = pathlib.Path.cwd()
    self.parent = parent
    self.isolate = isolate
    self.inherit = inherit
    self._config = config
    self._maindir = maindir
    self.require = Require(self, self.maindir)
    self.extensions = [extensions.ImportSyntax(), extensions.NamespaceSyntax()]
    self.resolver = resolver.StdResolver([], [loader.PythonLoader()]) #, loader.PackageRootLoader()])
    self.resolvers = []
    self.pathaugmentors = [base.ZipPathAugmentor()]
    self.modules = {}
    self.packages = {}
    self.module_stack = []
    self.main_module = None
    self.localimport = localimport.localimport([])
    self.tracer = None

  @property
  def config(self):
    if self._config is not None or not self.parent:
      return self._config
    return self.parent.config

  @property
  def maindir(self):
    if self._maindir is not None or not self.parent:
      return self._maindir
    return self.parent.maindir

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

    # Add the pip prefix directory to the path from the first nodepy
    # directory that can be found.
    add_path = []
    for path in utils.path.upiter(pathlib.Path.cwd()):
      path = path.joinpath(self.pipprefix_directory)
      if path.is_dir():
        if os.name == 'nt':
          path = path.joinpath('Lib')
        else:
          path = path.joinpath('lib', 'python' + sys.version[:3])
        if path.is_dir():
          add_path.append(str(path))
          add_path.append(str(path.joinpath('site-packages')))
        break

    with utils.context.ExitStack() as stack:
      stack.add(activate_localimport())
      sys.path.extend(add_path)
      stack.add(reload_pkg_resources())
      sys.path_importer_cache.clear()
      yield

  def augment_path(self, path):
    for augmentor in self.pathaugmentors:
      path = augmentor.augment_path(path)
    return path

  def resolve(self, request, directory=None, additional_search_path=()):
    """
    Checks all resolvers in this context to determine the module matching
    the specified *request*. If the context has a parent, it will be used
    for resolving the request as well.

    If the sub-context is configured to be isolated from its parent (which it
    is by default), modules resolved by the parent will be associated with
    the sub-context instead and they will not be registered on the parent.

    Additionally, if the sub-context is configured to *inherit* already loaded
    modules from its parent, a module that is resolved by the sub-context will
    first be checked for an already loaded module in the parent (on by default).
    """

    if isinstance(request, six.string_types):
      request = base.RequestString(request)
    elif isinstance(request, pathlib.Path):
      request = base.RequestPath(request)
    if not isinstance(request, base.Request):
      if directory is None:
        directory = self.maindir
      request = base.Request(self, directory, request, additional_search_path)

    # Check all resolvers in the context.
    module = None
    exception = base.ResolveError(request)
    for resolver in chain([self.resolver], self.resolvers):
      try:
        module = resolver.resolve_module(request)
      except base.ResolveError as exc:
        assert exc.request is request, (exc.request, request)
        exception.append_from(exc)
        continue
      if not isinstance(module, base.Module):
        msg = '{!r} returned non-Module object {!r}'
        msg = msg.format(type(resolver).__name__, type(module).__name__)
        raise RuntimeError(msg)
      break

    # Check the parent.
    if self.parent and module and self.inherit:
      # Inherit the module that was already loaded by the parent.
      module = self.parent.modules.get(module.filename, module)
    elif self.parent and not module:
      assert isinstance(request, base.Request)
      if not self.isolate:
        request.context = self.parent
      try:
        module = self.parent.resolve(request, directory, additional_search_path)
      except base.ResolveError as exc:
        exception.append_from(exc)

    if module:
      have_module = request.context.modules.get(module.filename)
      if have_module is not None and have_module is not module:
        msg = '{!r} returned new Module object besides an existing entry '\
              'in the cache'.format(type(resolver).__name__)
        raise RuntimeError(msg)
      request.context.modules[module.filename] = module
      return module

    raise exception

  def register_module(self, module, force=False):
    """
    Adds a module to the Context, allowing it to be loaded using
    #load_module(). If *force* is not set to #True and a different module with
    the filename already exists, a #RuntimeError will be raised.

    Note that if an exception happens during #load_module(), the module will
    be unregistered again.
    """

    have_module = self.modules.get(module.filename)
    if have_module:
      if have_module is module:
        return
      if not force:
        msg = '{!r} a different module with that filename is already registered'
        raise RuntimeError(msg.format(module))
    self.modules[module.filename] = module

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
      six.reraise(*module.exception)
    if module.loaded:
      return

    have_module = self.modules.get(module.filename)
    if have_module is None:
      msg = '{!r} can not be loaded when not in Context.modules'
      raise RuntimeError(msg.format(module))
    if have_module is not module:
      msg = '{!r} is registered but has a different identitity'
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

  @contextlib.contextmanager
  def push_main(self, module):
    """
    A context-manager to temporarily shadow the #Context.main_module with
    the specified *module*.
    """

    if not isinstance(module, base.Module):
      raise TypeError('expected nodepy.base.Module instance')

    prev_module = self.main_module
    self.main_module = module
    try:
      yield
    finally:
      self.main_module = prev_module

  def __breakpoint__(self, tb=None, stackdepth=0):
    """
    Default implementation of the #breakpoint() method. Uses PDB.
    """

    if tb is not None:
      utils.FrameDebugger().interaction(None, tb)
    else:
      frame = sys._getframe(stackdepth+1)
      utils.FrameDebugger().set_trace(frame)

  def breakpoint(self, tb=None, stackdepth=0):
    """
    The default implementation of this method simply calls #__breakpoint__().
    It can be overwritten (eg. simply by setting the member on the #Context
    object) to alter the behaviour. This method is called by
    #Require.breakpoint().
    """

    self.__breakpoint__(tb, stackdepth+1)
