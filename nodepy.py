# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Node.py is a layer on top of the Python runtime which allows to load other
modules the Node.js way, using a require() function.

synopsis:
  nodepy                (interactive console)
  nodepy -c EXPR [...]  (evaluate EXPR)
  nodepy REQUEST [...]  (resolve REQUEST and execute it)
"""

from __future__ import absolute_import, division, print_function

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.21'
__license__ = 'MIT'

import abc
import argparse
import errno
import code
import collections
import contextlib
import itertools
import json, json as _json
import marshal
import math
import os
import pdb
import pstats
import py_compile
import re
import sys
import tempfile
import traceback
import types

try:
  import cProfile as profile
except ImportError:
  import profile

try:
  import pkg_resources
except ImportError:
  pkg_resources = None

try:
  reload
except NameError:
  try:
    from importlib import reload
  except ImportError:
    from imp import reload

try:
  import pygments.lexers, pygments.formatters
except ImportError:
  pygments = None

try:
  import colorama
except ImportError:
  # We need colorama on Windows for colorized output.
  if os.name == 'nt':
    pygments = None
else:
  colorama.init()

import localimport
import six

if sys.version >= '3.5':
  import importlib._bootstrap_external


# ====================
# Globals
# ====================

#: Arguments to spawn a Node.py child-process.
proc_args = [sys.executable, __file__]

#: The executbale that is running Node.py.
executable = None

#: Name of the Python implementation that we're running on.
python_impl = None
if hasattr(sys, 'implementation'):
  python_impl = sys.implementation.name.lower()
else:
  python_impl = sys.subversion[0].lower()

#: Node.py and Python versions and platform architecture.
VERSION = 'Node.py-{0} [{3} {1[0]}.{1[1]}.{1[2]} {2}-bit]'.format(
    __version__, sys.version_info, int(round(math.log(sys.maxsize, 2))) + 1,
    python_impl)

#: When a script is installed by NPPM, this will be a dictionary containing
#: information about the script, such as its install location ("root", "global"
#: or "local") and the original #sys.path before it was altered to include the
#: nodepy_modules/ directory.
script = None


# ====================
# Exceptions
# ====================

class NoSuchBindingError(Exception):
  pass


class ResolveError(Exception):

  def __init__(self, request):
    assert isinstance(request, Request)
    self.request = request

  def __str__(self):
    msg = "'{0}'".format(self.request.name)
    if self.request.is_main:
      msg += ' [main]'
    if self.request.current_dir:
      msg += " (from directory '{0}')".format(self.request.current_dir)
    if self.request.path:
      msg += ' searched in:\n  - ' + '\n  - '.join(map(repr, self.request.path))
    return msg


# ====================
# Packages & Modules
# ====================

class ExtensionHandlerRunner(object):
  """
  This class is used to invoke handler functions on extension modules and
  objects. It supports stepwise modification of each subsequent handler
  call by invoking a *collector* function after every handler.
  """

  def __init__(self, handler_name, runner, require=None, module=None,
               package=None, context=None, result=None):
    self.handler_name = handler_name
    self.runner = runner
    if not require:
      if module:
        require = module.require
      elif package:
        require = package.require
      else:
        require = context.require
    self.require = require
    self.module = None
    self.package = package
    self.context = context
    self.result = result

  def __call__(self, ext):
    if isinstance(ext, str):
      ext = self.require(ext)
    try:
      handler = getattr(ext, self.handler_name)
    except AttributeError:
      return
    self.runner(self, handler)

  def runall(self, extensions, require=None):
    if require is None:
      require = self.require
    for ext in extensions:
      init = ext not in require.cache
      module = require(ext)
      if init and hasattr(module, 'init_extension'):
        module.init_extension(self.package, self.module)
      self(module)
    return self.result

  @classmethod
  def wrap(cls, handler_name, *args, **kwargs):
    def decorator(func):
      return cls(handler_name, func, *args, **kwargs)
    return decorator


class Package(object):
  """
  Represents a `package.json` file. If a module is loaded that lives near
  such a manifest, that module will be associated with the #Package.
  """

  def __init__(self, context, filename, json=None):
    if json is None:
      with open(filename) as fp:
        json = _json.load(fp)
    self.context = context
    self.filename = filename
    self.json = json
    self.module = JsonModule(context, filename, package=self)
    self.extensions = list(json.get('extensions', []))

    directory = self.directory
    self.vendor_directories = json.get('vendor-directories', [])
    self.vendor_directories = [normpath(x, directory) for x in self.vendor_directories]

  def __repr__(self):
    return "<Package '{}@{}' at '{}'>".format(
      self.json.get('name'), self.json.get('version'), self.filename)

  @property
  def directory(self):
    return os.path.dirname(self.filename)

  @property
  def require(self):
    return self.module.require


class BaseModule(six.with_metaclass(abc.ABCMeta)):
  """
  Represents a Python module that exposes members like data, functions and
  classes in its #namespace. In some cases, when a module is loaded from a
  specific file, a cached version is chosen instead and the real filename
  is different. The module is still stored under the original filename, as
  that is the name it will be resolved as when the module is requested. That's
  when the *real_filename* is different from the *filename* attribute.

  (Storing it under the cache name would actually lead to cache misses).
  """

  def __init__(self, context, filename, directory, name, package=None,
               request=None, real_filename=None, extensions=None,
               vendor_directories=None):
    self.context = context
    self.filename = filename
    self.real_filename = real_filename or filename
    self.directory = directory
    self.name = name
    self.namespace = types.ModuleType(str(name))  # in Python 2, does not accept Unicode
    self.require = Require(self)
    self.executed = False
    self.exec_mtime = None
    self.request = request
    self.package = package
    self.extensions = [] if extensions is None else extensions
    self.vendor_directories = [] if vendor_directories is None else vendor_directories
    self.vendor_directories = [normpath(x, directory) for x in self.vendor_directories]
    self.reload_pass = 0
    self.init_namespace()

  def __repr__(self):
    return "<{} from '{}'>".format(type(self).__name__, self.filename)

  def init_namespace(self):
    self.namespace.__file__ = self.real_filename
    self.namespace.__name__ = self.name
    self.namespace.require = self.require
    self.namespace.module = self
    if self.directory:
      self.namespace.__directory__ = self.directory

  def remove(self):
    """
    Removes the module from the #Context._module_cache.
    """

    del self.context._module_cache[self.filename]

  @property
  def parent(self):
    if self.request:
      return self.request.parent_module
    return None

  @abc.abstractmethod
  def exec_(self):
    """
    Execute the module. If #BaseModule.executed is #True, a #RuntimeError
    should be raised. If an error occurs during the module's execution,
    #BaseModule.remove() must be called!

    It is also very important to call the parent implementation of #exec_()
    as it will set the #exec_mtime member and #executed to #True.

    This method must be called before the module's code is ACTUALLY
    executed to ensure that #executed is set to #True and the #exec_mtime
    is valid so that #source_changed is #False after the module is executed.
    """

    if self.executed:
      raise RuntimeError('already executed')
    self.executed = True

    mtime = 0.0
    if self.real_filename and os.path.exists(self.real_filename):
      mtime = os.path.getmtime(self.real_filename)
    if self.filename and os.path.exists(self.filename):
      mtime = max(mtime, os.path.getmtime(self.filename))
    self.exec_mtime = mtime

  def reload(self):
    """
    Called to reload the code of the module. The default implementation
    is just a sequence of the following:

    1. #init_namespace()
    2. set #executed to #False
    4.  #exec_().
    """

    self.init_namespace()
    self.executed = False
    self.exec_()

  @property
  def source_changed(self):
    """
    Returns true if the source that the module was loaded from has changed. The
    default implementation compares the higher modification times of
    #real_filename and #filename against the modification time saved when the
    module was executed with #exec_() (which also takes the higher modification
    time of the two).
    """

    if self.exec_mtime is None:
      return True

    mtime = 0.0
    if self.real_filename and os.path.exists(self.real_filename):
      mtime = os.path.getmtime(self.real_filename)
    if self.filename and os.path.exists(self.filename):
      mtime = max(mtime, os.path.getmtime(self.filename))
    return mtime > self.exec_mtime


class InitModule(BaseModule):
  """
  A proxy module that is used as the entry point into Node.py modules or as
  the container for the interactive session.
  """

  def __init__(self, context):
    super(InitModule, self).__init__(context, '__init__', context.current_dir, '__init__')

  def exec_(self):
    raise RuntimeError('can not exec InitModule')


# ====================
# Basic Resolve & Loading Mechanism
# ====================

ParsedRequestString = collections.namedtuple('ParsedRequestString', 'package path')


def split_request_string(request):
  """
  Splits a string that represents a request for a module into two parts: The
  package name and the name of the module that is requested inside that
  package.

  Returns #None if *request* is a path or a relative request.
  """

  if os.path.isabs(request):
    return None
  if request in '..' or request.startswith('./') or request.startswith('../'):
    return None

  parts = request.split('/')
  if parts and parts[0].startswith('@'):
    scope = parts.pop(0)
  else:
    scope = None
  if not parts:
    return None

  package = parts.pop(0)
  if scope:
    package = '@' + scope + '/' + package
  return ParsedRequestString(package, '/'.join(parts))


class Request(object):
  """
  Represents a request-string that is to be resolved with all the context
  information included.

  # Arguments
  name (str): The string that is used to resolve the request (that is,
    the name of the module to load).
  current_dir (str): The current directory in which relative requests are
    being resolved in. Note that if #is_main is #True, absolute requests
    will also be resolved in that directory.
  is_main (bool): #True if the request is supposed to be loaded as the main
    main module of the current execution.
  path (list of str): A list of additional search paths. Usually these are
    filesystem paths, but they may also be something entirely different and
    only then taken into account by a specific loader if the format matches.
  parent_module (BaseModule): A module object that requested to resolve this
    request. Note that for the first module that is being resolved, this will
    be an #InitModule instance.
  context (Context): The context that manages the whole runtime.

  # Members
  data (any): A data member that can be filled by the #BaseResolver that
    finally returns a #BaseLoader object from #BaseResolver.resolve() in
    order to communicate the information that has been determined during
    the resolve procedure to the loader. Alternatively, a new loader object
    can be constructed and the information passed to its constructor.
  original_resolve_location (str): Set by resolvers when a package link is
    encountered to enable the module loader to use the correct nodepy_modules/
    directory inside the module.
  """

  def __init__(self, name, current_dir, is_main, path, parent_module, context):
    self.name = name
    self.current_dir = current_dir
    self.is_main = is_main
    self.path = path
    self.parent_module = parent_module
    self.context = context
    self.clear_state()

  def clear_state(self):
    self.data = None
    self.original_resolve_location = None


class BaseResolver(six.with_metaclass(abc.ABCMeta)):
  """
  Base class for objects that implement resolving module requests and return
  some other object that can load that module.
  """

  @abc.abstractmethod
  def resolve(self, request):
    """
    Resolve the *request* which must be a #Request instance and return a
    #BaseLoader instance. This #BaseLoader may be a completely new instance
    or an existing object. The latter is usually preferred for loading
    processes where #Request.data is simply adjusted.
    """


class BaseLoader(six.with_metaclass(abc.ABCMeta)):
  """
  Base class for objects that can load #BaseModule objects.
  """

  @abc.abstractmethod
  def get_filename(self, request):
    """
    Determine a string that uniquely identifies the module that is about to
    be loaded with this loader. For example, for loaders that load from the
    filesystem, this is the canonical and normalized filename.

    Note that the very same filename MUST be passed to the #BaseModule.
    """

  @abc.abstractmethod
  def load(self, request):
    """
    Load and return the #BaseModule object for the specified #Request.
    Depending on the implementation of the #Loader, the *request* may
    have been modified to contain the information that has been determined
    in #BaseResolver.resolve() or that information might have been passed
    to the loader on construction.
    """


class FilesystemResolver(BaseResolver):
  """
  Resolves requests on the filesystem. Requires #FilesystemLoaderSupport
  objects to be registered to the resolver.
  """

  CacheEntry = collections.namedtuple('CacheEntry', 'filename, support, orl')

  def __init__(self):
    self.supports = []
    self.index_files = ['index', '__init__']
    self.cache = {}

  def add_support(self, support):
    if not isinstance(support, FilesystemLoaderSupport):
      raise TypeError('expected FilesystemLoaderSupport')
    self.supports.append(support)

  def resolve(self, request):
    filename, support = self._resolve(request, request.name)
    if not support:
      for support in self.supports:
        if support.can_load(filename):
          break
      else:
        raise ResolveError(request)
    return support.get_loader(filename, request)

  def _resolve(self, request_obj, request, package=None, parent_info=None):
    current_dir = request_obj.current_dir
    info = split_request_string(request)

    # Resolve relative requests by creating an absolute path and try
    # to resolve that instead.
    if not info and not os.path.isabs(request):
      assert current_dir
      new_request = os.path.abspath(os.path.join(current_dir, request))
      return self._resolve(request_obj, new_request)

    # Absolute paths will be resolved only with the FilesystemLoaderSupport's
    # can_load() and suggest_try_files() methods.
    elif not info:
      request, original_request = normpath(request), request

      # Check if we have cached what this request leads us to.
      cache = self.cache.get(request)
      if cache is not None:
        request_obj.original_resolve_location = cache.orl
        return cache.filename, cache.support

      def cache_and_return(filename, support):
        entry = self.CacheEntry(filename, support, request_obj.original_resolve_location)
        self.cache[request] = entry
        if original_request != request:
          self.cache[original_request] = entry
        return filename, support

      # Determine if the request is pointing to a file in a directory that
      # is actually just a link to another directory.
      link = get_package_link(request)
      if link:
        if not request_obj.original_resolve_location:
          request_obj.original_resolve_location = link.src
        request = os.path.join(link.dst, os.path.relpath(request, link.src))

      # If the file exists as it is, we will use it as it is.
      filename = try_file(request)
      if filename:
        return cache_and_return(filename, None)

      # Alternatively, try all the files suggested by the loader support.
      for support in self.supports:
        for filename in support.suggest_try_files(request):
          filename = try_file(filename)
          if filename:
            return cache_and_return(filename, support)

      if os.path.isdir(request):
        # If there is a package.json file in this directory, we can parse
        # it for its "main" field to find the file we should be requiring
        # for this directory.
        if package and parent_info and not parent_info.path:
          main = package.json.get('main') if package else None
        else:
          main = None
        if main:
          new_request = os.path.join(request, str(main))
          filename, support = self._resolve(request_obj, new_request)
          return cache_and_return(filename, support)
        else:
          # Otherwise, try the standard index files.
          for choice in self.index_files:
            new_request = os.path.join(request, choice)
            try:
              filename, support = self._resolve(request_obj, new_request)
              return cache_and_return(filename, support)
            except ResolveError:
              continue

      # Dunno what to do with this absolute request.
      raise ResolveError(request_obj)

    # This is a pure module request that we have to search for in the
    # search path.
    assert info
    if current_dir is None and request_obj.is_main:
      current_dir = '.'
    if current_dir:
      new_request = os.path.abspath(os.path.join(current_dir, request))
      try:
        return self._resolve(request_obj, new_request)
      except ResolveError:
        pass

    path = list(request_obj.path)
    nodepy_modules = find_nearest_modules_directory(current_dir)
    if nodepy_modules:
      path.insert(0, nodepy_modules)
    if request_obj.is_main:
      path.insert(0, current_dir)

    for directory in path:
      directory = os.path.abspath(directory)
      package_dir = os.path.join(directory, info.package)
      if not os.path.isdir(package_dir):
        continue

      link = get_package_link(package_dir)
      if link:
        if not request_obj.original_resolve_location:
          request_obj.original_resolve_location = link.src
        package_dir = link.dst

      # Take into account the 'resolve_root' of the package manifest.
      package = request_obj.context.get_package_for(
        package_dir, doraise=False)

      if package and 'resolve_root' in package.json:
        new_request = os.path.join(package_dir, package.json['resolve_root'], info.path)
      else:
        new_request = os.path.join(package_dir, info.path)

      try:
        return self._resolve(request_obj, new_request, package, info)
      except ResolveError:
        pass

    raise ResolveError(request_obj)


class FilesystemLoaderSupport(six.with_metaclass(abc.ABCMeta)):
  """
  This interface is used in the #FilesystemResolver to determine whether a
  specific file can be loaded, and then create a #BaseLoader object for that
  file.
  """

  @abc.abstractmethod
  def suggest_try_files(self, filename):
    pass

  @abc.abstractmethod
  def can_load(self, filename):
    pass

  @abc.abstractmethod
  def get_loader(self, filename, request):
    pass


# ====================
# Python Support
# ====================

class PythonFilesystemLoaderSupport(FilesystemLoaderSupport):

  def __init__(self, write_bytecache=None):
    self.write_bytecache = write_bytecache

  def suggest_try_files(self, filename):
    yield filename + '.py'
    yield filename + PythonLoader.pyc_suffix

  def can_load(self, filename):
    return filename.endswith('.py') or filename.endswith(PythonLoader.pyc_suffix)

  def get_loader(self, filename, request):
    return PythonLoader(filename, write_bytecache=self.write_bytecache)


class PythonLoader(BaseLoader):

  #: Implementation and version dependent suffix.
  pyc_suffix = '.{}-{}{}.pyc'.format(python_impl.lower(), *sys.version_info)

  def __init__(self, filename, write_bytecache=None, python_module_class=None):
    if write_bytecache is None:
      write_bytecache = not bool(os.getenv('PYTHONDONTWRITEBYTECODE', '').strip())
    self.filename = filename
    self.write_bytecache = write_bytecache
    self.python_module_class = python_module_class or PythonModule

  def get_filename(self, request):
    return self.filename

  def load(self, request):
    """
    Loads the Python module from the filename passed to #__init__().
    If #write_bytecache is #True and the filename is already a cache
    file, a bytecache will be generated if possible.
    """

    filename_noext = os.path.splitext(self.filename)[0]
    name = os.path.basename(filename_noext)

    return self.python_module_class(
      context=request.context,
      filename=self.filename,
      name=name,
      request=request,
      package=request.context.get_package_for(self.filename),
      extensions=None,
      loader=self
    )

  def exec_(self, module):
    filename = self.filename
    filename_noext = os.path.splitext(filename)[0]
    bytecache_file = filename_noext + self.pyc_suffix

    context = module.context
    package = context.get_package_for(filename)

    if os.path.isfile(bytecache_file) and os.path.isfile(filename) and \
        os.path.getmtime(bytecache_file) >= os.path.getmtime(filename):
      can_load_bytecache = True
    else:
      can_load_bytecache = False

    if not can_load_bytecache and self.write_bytecache:
      try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
          try:
            with open(filename, 'r') as src:
              source, extensions = self._preprocess(context, package, filename, src.read())
              tmp.write(source)
              # FIXME: Save extensions into the bytecompile-file.
            tmp.close()
            py_compile.compile(tmp.name, cfile=bytecache_file, dfile=filename, doraise=True)
          finally:
            # Make sure the temporary file is deleted.
            try:
              os.remove(tmp.name)
            except OSError as exc:
              if exc.errno != errno.ENOENT:
                print_exc()
      except OSError as exc:
        if exc.errno != errno.EPERM:
          print_exc()
        # Skip permission errors.
      except Exception as exc:
        print_exc()
      else:
        can_load_bytecache = True

    if can_load_bytecache:
      try:
        code, extensions = self.load_code(context, package, bytecache_file, is_compiled=True)
        real_filename = bytecache_file
      except PermissionError:
        can_load_bytecache = False

    if not can_load_bytecache:
      code, extensions = self.load_code(context, package, filename, is_compiled=None)
      real_filename = None

    module.extensions = extensions
    module.filename = filename
    module.real_filename = real_filename
    module.code = code

    BaseModule.exec_(module)
    exec(code, vars(module.namespace))

  @staticmethod
  def _iter_lines(string):
    """
    Efficiently iterate over the lines of a string.
    """

    prevnl = -1
    while True:
      nextnl = string.find('\n', prevnl + 1)
      if nextnl < 0: break
      yield string[prevnl + 1:nextnl]
      prevnl = nextnl

  def _preprocess(self, context, package, filename, source):
    # Find per-source code extensions.
    extensions = []
    for line in self._iter_lines(source):
      if not line.startswith('#'): break
      line = line[1:].lstrip()
      if line.startswith('nodepy-extensions:'):
        extensions = line[18:].split(',')
        break

    extensions = [x.strip() for x in extensions]
    module_extensions = extensions[:]
    if package:
      extensions += package.extensions

    # Cumulatively invoke the preprocess handler.
    @ExtensionHandlerRunner.wrap('preprocess_python_source',
      package=package, context=context, result=source)
    def runner(self, handler):
      self.result = handler(package, filename, self.result)

    runner.runall(extensions)
    return runner.result, module_extensions

  def load_code(self, context, package, filename, is_compiled=None):
    """
    Loads a Python code object from a file. If *is_compiled*, it will be
    treated as a bytecompiled file if it ends with `.pyc`, otherwise it will
    be loaded as Python source. Note that any syntactical errors might be
    raised when the file is loaded as source.
    """

    if is_compiled is None:
      is_compiled = filename.endswith('.pyc')
    if is_compiled:
      with open(filename, 'rb') as fp:
        if sys.version >= '3.5':
          importlib._bootstrap_external._validate_bytecode_header(fp.read(12))
        else:
          header_size = 12 if sys.version >= '3.3' else 8
          fp.read(header_size)
        # FIXME: Load extensions from the bytecompiled file.
        return marshal.load(fp), []
    else:
      with open(filename, 'r') as fp:
        source, extensions = self._preprocess(context, package, filename, fp.read())
        return compile(source, filename, 'exec', dont_inherit=True), extensions


class PythonModule(BaseModule):
  """
  Represents a Node.py Python module object that is executed from a code
  object. The #PythonLoader is responsible for loading the code from files
  respectively.
  """

  def __init__(self, context, filename, name, package, request,
               extensions, loader):
    super(PythonModule, self).__init__(
        context=context, filename=filename, package=package,
        directory=os.path.dirname(filename), name=name,
        request=request, extensions=extensions)
    self.code = None
    self.loader = loader

  def exec_(self):
    # BaseModule.exec_() is called by the PythonLoader.exec_() after
    # the bytecache was created.
    try:
      with self.context.enter_module(self):
        self.loader.exec_(self)
    except:
      self.remove()
      raise


# ====================
# JSON Support
# ====================

class JsonFilesystemLoaderSupport(FilesystemLoaderSupport):

  def __init__(self, suggest_json_suffix=False):
    self.suggest_json_suffix = suggest_json_suffix

  def suggest_try_files(self, filename):
    if self.suggest_json_suffix:
      yield filename + '.json'

  def can_load(self, filename):
    return filename.endswith('.json')

  def get_loader(self, filename, request):
    return JsonLoader(filename)


class JsonLoader(BaseLoader):

  def __init__(self, filename):
    self.filename = filename

  def get_filename(self, request):
    return self.filename

  def load(self, request):
    filename = self.filename
    package = request.context.get_package_for(filename)
    if os.path.basename(filename) == 'package.json':
      assert isinstance(package, Package), package
      assert normpath(os.path.abspath(filename)) == \
        normpath(os.path.abspath(filename))
      return package.module
    return JsonModule(request.context, filename, request=request, package=package)


class JsonModule(BaseModule):

  def __init__(self, context, filename, request=None, package=None):
    directory, name = os.path.split(filename)
    super(JsonModule, self).__init__(
      context=context, filename=filename, directory=directory, name=name,
      request=request, package=package)

  def exec_(self):
    super(JsonModule, self).exec_()
    if os.path.basename(self.filename) == 'package.json' and self.package:
      self.namespace.exports = self.package.json
    else:
      with open(self.filename, 'r') as fp:
        self.namespace.exports = json.load(fp)


# ====================
# Extensions
# ====================

class RequireUnpackSyntaxExtension(object):
  """
  This is an extension that is registered to the #Context as a binding
  that preprocesses Python source code to allow unpacking of members from
  a `require()` call.

  # Example
  ```python
  { app, config } = require('./app')

  # equivalent of
  temp = require('./app')
  app = temp.app
  config = temp.config
  del temp
  ```
  """

  _regex = re.compile(
    r'''{\s*(?!,)(?P<members>\w+(?:\s+as\s+\w+)?(?:\s*,\s*\w+)*)\s*,?\s*}\s*=\s*require\((?P<q>["'])(?P<mod>.*?)(?P=q)\)'''
  )

  def preprocess_python_source(self, package, filename, code):
    while True:
      # TODO: This currently does not support nested expressions in the require() call.
      # TODO: We can optimize this by passing a start index.
      match = self._regex.search(code)
      if not match: break
      stmt = self.import_symbols_from_stmt(match.group('mod'), match.group('members').split(','))
      code = code[:match.start(0)] + stmt + code[match.end(0):]
    return code

  @staticmethod
  def import_symbols_from_stmt(module, symbols):
    stmt = '_reqres=require({!r}, exports=False).namespace;'.format(module)
    for name in symbols:
      alias = name = name.strip()
      parts = re.split('\s+', name)
      if len(parts) == 3 and parts[1] == 'as':
        name, __, alias = parts
      stmt += '{0}=_reqres.{1};'.format(alias, name)
    return stmt + 'del _reqres'


class RequireImportSyntaxExtension(object):
  """
  Similar to the #RequireUnpackSyntaxExtension, this extension allows the use
  of JavaScript-like ES6 module imports. These look very similar to Python
  imports.

  # Examples & Explanations

  Import the default member from the specified module. If no member is
  exported in the module, the module itself is returned. Note that this is
  the same as `require()`-ing the module. The two statements below are
  equivalent.

      import default_member from "module-name"

  You can also avoid importing the default member by using this syntax instead:

      import "module-name" as defaultMember

  The module can also be imported without exporting a symbol into the current
  namespace, just for the side-effects of the module import.

      import "module-name"

  Import a single member from a module. This inserts `myMember` into the
  current scope.

      import {myMember} from "module-name"

  Import multiple members of a module.

      import {foo, bar} from "module-name"

  Import a member under a different name. Note how line-breaks are supported
  in this new import statement syntax (it is still not supported in the old
  Python import).

      import {reallyReallyLongMemberName as shortName}
          from "module-name"

  You can also import the default member and other members.

      import default_member, {member1, reallyReallyLongMemberName as shortName}
          from "module-name"

  To import all public members of a module (which is either all members
  without an underscore prefix or all listed in the `__all__` member), use
  starred import.

      import * from "module-name"

  You can import the actual module object additionally to the starred
  import with the following syntax:

      import module, * from "module-name"

  It is also possible to assign the imported name as a member to an existing
  object in the scope.
  """

  _re_import_as = re.compile(
    r'''^(?P<indent>[^\S\n]*)import\s+(?P<q>"|')(?P<mod>.*?)(?P=q)(?:\s+as\s+(?P<n>[\.\w]+))?[^\S\n]*$''',
    re.M
  )
  _re_import_from = re.compile(
    r'''
    ^(?P<indent>[^\S\n]*)   # Keep track of the indentation level
    import\s+
    (?P<members>
      (?:
        [\.\w]+|            # Default member
        (?:[\.\w]+\s*,\s*)?     # Default member + specific members
      )?
      (?:
        \{[^}]+\}|          # Specific members
        \*                  # Starred-import
      )?
    )\s+
    from\s+
    (?P<q>["'])(?P<mod>.*)(?P=q)[^\S\n]*$
    ''',
    re.M | re.X
  )
  _regexes = [(_re_import_as, 'as'), (_re_import_from, 'from')]

  def preprocess_python_source(self, package, filename, source):
    while True:
      for regex, kind in self._regexes:
        match = regex.search(source)
        if match: break
      else:
        break

      if kind == 'as':
        as_name = match.group('n')
        if as_name:
          repl = '{}=require({!r})'.format(as_name, match.group('mod'))
        else:
          repl = 'require({!r})'.format(match.group('mod'))
      elif kind == 'from':
        module = match.group('mod')
        members = match.group('members')
        if members == '*':
          repl = 'require.symbols({!r})'.format(module)
        elif '{' in members:
          if members.startswith('{'):
            default_name = None
          else:
            default_name, members = members.partition(',')[::2]
            members = members.lstrip()
            assert members.startswith('{')
          assert members.endswith('}')
          repl = RequireUnpackSyntaxExtension.import_symbols_from_stmt(
            module, members[1:-1].split(',')
          )
          if default_name:
            repl = '{}=require({!r});'.format(default_name, module) + repl
        elif members.endswith('*') and members.count(',') == 1:
          default_member = members.split(',')[0].strip()
          repl = 'require.symbols({0!r}); {1}=require({0!r})'.format(module, default_member)
        else:
          repl = '{}=require({!r})'.format(members, module)
      else:
        raise RuntimeError

      # Add additional newlines to the replacement until it spans
      # the same number of newlines than the matched sequence. This
      # is to keep error message more consistent.
      repl = match.group('indent') + repl + '\n' * match.group(0).count('\n')

      source = source[:match.start()] + repl + source[match.end():]

    return source


# ====================
# Runtime Layer
# ====================

class Require(object):
  """
  The `require()` function for #PythonModule#s.
  """

  NoSuchBindingError = NoSuchBindingError
  ResolveError = ResolveError
  PY2 = six.PY2
  PY3 = six.PY3

  # An ever increasing index that is used to avoid infinite recursion
  # during cascade reloading.
  reload_pass = 0

  def __init__(self, module):
    self.module = module
    self.path = []
    self.cache = {}

    # Find the nearest modules directory for this module.
    self.nearest_modules = None
    if self.module.filename:
      self.nearest_modules = find_nearest_modules_directory(self.module.filename)

  @property
  def context(self):
    return self.module.context

  @property
  def main(self):
    return self.module.context.main_module

  @main.setter
  def main(self, module):
    if module is not None and not isinstance(module, BaseModule):
      raise TypeError('main must be None or BaseModule')
    self.module.context.main_module = None

  @property
  def current(self):
    return self.context.current_module

  def __repr__(self):
    return '<require() of module {!r}>'.format(self.module.name)

  def __call__(self, request, current_dir=None, is_main=False, cache=True,
               exports=True, exec_=True, into=None, symbols=None, loader=None):
    """
    Resolve *request* into a module filename and load that module. For relative
    paths, the *current_dir* will be used to resolve the request (defaults to
    the parent directory of the module that owns the #Require instance). If
    the request starts with `!` (exclamation mark), the request will be
    forwarded to #Context.binding().

    If *is_main* is True, non-relative requests will also be resolved in the
    *current_dir* first. Note that the #Context will raise a #RuntimeError when
    there is already a #Context.main_module, thus it is recommended to use
    #exec_main().

    If *cache* is False, the request will not be cached and also not be looked
    up into the cache.

    If *exports* is False, the actual #BaseModule object is returned, otherwise
    the #BaseModule.namespace or even #BaseModule.namespace.exports member if
    exists.

    If *exec_* is False, the module will only be loaded and not be executed.
    Note that the module may have already been loaded on another occassion!

    If *into* is specified, this function behaves like a Python star-import and
    will import all members of the module that would normally be returned into
    the specified dictionary. Usually, you'll want to pass `globals()` to this
    parameter.
    """

    if request.startswith('!'):
      binding = self.context.binding(request[1:])
      self.cache[request] = binding
      return binding

    if cache and request in self.cache:
      AUTORELOAD = 'require.autoreload'
      CASCADEBLOCK = 'require.autoreload.cascadeblock'
      module = self.cache[request]
      autoreload = self.context.options.get(AUTORELOAD)
      if exec_ and autoreload in ('on', True) and module.source_changed:
        module.reload()
        assert not module.source_changed, "source still changed after module reload"
      elif exec_ and autoreload == 'cascade' and not self.context.options.get(CASCADEBLOCK):
        # Reload the module recursively.
        Require.reload_pass += 1
        def recursive_reload(module):
          changed = module.source_changed
          for dependency in module.require.cache.values():
            if recursive_reload(dependency):
              changed = True
          if changed and Require.reload_pass != module.reload_pass:
            module.reload()
            module.reload_pass = Require.reload_pass
            assert not module.source_changed, "source still changed after module reload"
            changed = True
          return changed
        try:
          self.context.options[CASCADEBLOCK] = True
          recursive_reload(module)
        finally:
          self.context.options.pop(CASCADEBLOCK, None)

    else:
      current_dir = current_dir or self.module.directory
      self.context.send_event(Context.Event_Require, {
          'request': request, 'current_dir': current_dir,
          'is_main': is_main, 'cache': cache, 'parent': self.module}
      )

      # Resolve and load the module.
      module = self.context.resolve_and_load(request, current_dir=current_dir,
        additional_path=self.path, is_main=is_main, exec_=exec_, cache=cache)
      if cache:
        self.cache[request] = module
      if exec_:
        assert not module.source_changed, "module source changed directly after load"

    if exports:
      module = get_exports(module)

    if into is not None:
      if symbols is None:
        symbols = getattr(module, '__all__', None)
      if symbols is not None:
        for key in symbols:
          into[key] = getattr(module, key)
      else:
        for key in dir(module):
          if not key.startswith('_') and key not in ('module', 'require'):
            into[key] = getattr(module, key)

    return module

  def symbols(self, request, symbols=None):
    if isinstance(symbols, str):
      if ',' in symbols:
        symbols = [x.strip() for x in symbols.split(',')]
      else:
        symbols = symbols.split()
    into = sys._getframe(1).f_locals
    return self(request, into=into, symbols=symbols)

  @contextlib.contextmanager
  def hide_main(self, argv=None):
    """
    Context manager to temporarily swap out the current main module, allowing
    you to execute another main module. Optionally, `sys.argv` can be
    temporarily overwritten, too.
    """

    main, self.main = self.main, None
    argv, sys.argv = sys.argv, sys.argv if argv is None else argv
    try:
      yield
    finally:
      sys.argv = argv
      self.main = main

  def exec_main(self, request, current_dir=None, argv=None, cache=True,
                exec_=True, exports=True, inherit_path=False):
    """
    Uses #hide_main() to temporarily swap out the current main module and
    loading another module as main. Returns the loaded module.
    """

    try:
      if inherit_path:
        self.context.path.extend(self.path)
      with self.hide_main(argv=argv):
        return self(request, current_dir, is_main=True, cache=cache,
                    exec_=exec_, exports=exports)
    finally:
      if inherit_path:
        for path in self.path:
          try:
            self.context.path.remove(path)
          except ValueError:
            pass

  def resolve(self, request):
    """
    Resolves a request to a filename.
    """

    return self(request, exec_=False, exports=False).filename


class Context(object):
  """
  The context encapsulates the execution of Python modules. It serves as the
  central unit to control the finding, caching and loading of Python modules.
  """

  #: Dispatched on a require() request.
  Event_Require = 'require'
  #: Dispatched when an module is loaded.
  Event_Load = 'load'
  #: Dispatched when a module is executed.
  Event_Enter = 'enter'
  #: Dispatched when a module is done being executed.
  Event_Leave = 'leave'

  def __init__(self, current_dir='.', bare=False, isolated=True):
    self.options = {}
    self.current_dir = current_dir
    self.isolated = isolated
    # Container for internal modules that can be bound to the context
    # explicitly with the #register_binding() method.
    self._bindings = {}
    # A list of filenames that are looked into when resolving a request to
    # a directory.
    self._index_files = ['index', '__init__']
    # A cache for the package.json files that needed to be parsed while
    # resolving require requests.
    self._package_cache = {}
    # Container for cached modules. The keys are the absolute and normalized
    # filenames of the module so that the same file will not be loaded multiple
    # times.
    self._module_cache = {}
    # A stack of modules that are currently being executed. Every module
    # should add itself on the stack when it is executed with #enter_module().
    self._module_stack = []
    self._package_stack = []
    # require() request resolvers.
    self.resolvers = []
    # A list of functions that are called for various events. The first
    # arugment is always the event type, followed by the event data.
    self.event_handlers = []
    # A list of additional search directories. Defaults to the paths specified
    # in the `NODEPY_PATH` environment variable.
    self.path = list(filter(bool, os.getenv('NODEPY_PATH', '').split(os.pathsep)))
    # TODO: Since we're using the nearest nodepy_modules/ directory
    #       automatically, we should not need to add this directory
    #       to the path.
    self.path.insert(0, 'nodepy_modules')
    # The main module. Will be set by #load_module().
    self.main_module = None
    # The initial module object, used to have access to #require.
    self.init = InitModule(self)

    # Localimport context for Python modules installed via Pip through nppm.
    # Find the location of where Pip modules would be installed into the Node.py
    # modules directory and add it to the importer.
    nearest_modules = find_nearest_modules_directory(current_dir)
    if not nearest_modules:
      nearest_modules = os.path.join(current_dir, 'nodepy_modules')
    pip_lib = get_site_packages(os.path.join(nearest_modules, '.pip'))
    self.importer = localimport.localimport(parent_dir=current_dir, path=[pip_lib])

    if not bare:
      fs = FilesystemResolver()
      fs.add_support(PythonFilesystemLoaderSupport())
      fs.add_support(JsonFilesystemLoaderSupport())
      self.resolvers.append(fs)
      self.register_binding('require-unpack-syntax', RequireUnpackSyntaxExtension())
      self.register_binding('require-import-syntax', RequireImportSyntaxExtension())

  def __enter__(self):
    self.importer.__enter__()
    if not self.isolated:
      # FIXME: Add function to localimport to update the environment without
      # preserving the original state.
      self.importer.meta_path = []
      self.importer.in_context = False
      del self.importer.state
    reload_pkg_resources(insert_paths_index=len(self.importer.path))
    return self

  def __exit__(self, *args):
    if self.isolated:
      try:
        return self.importer.__exit__(*args)
      finally:
        reload_pkg_resources()

  @property
  def require(self):
    return self.init.require

  @property
  def current_module(self):
    return self._module_stack[-1] if self._module_stack else None

  @property
  def current_modules(self):
    return self._module_stack

  @contextlib.contextmanager
  def enter_module(self, module):
    """
    Adds the specified *module* to the stack of currently executed modules.
    A module can not add itself more than once to the stack at a time. This
    method is a context-manager and must be used as such.
    """

    if not isinstance(module, BaseModule):
      raise TypeError('module must be a BaseModule instance')
    if module in self._module_stack:
      raise RuntimeError('a module can only appear once in the module stack')

    # If the module is near a `nodepy_modules/` directory, we want to be able
    # to import from that directory as well.
    library_path = None
    nearest_modules = None
    if module.filename:
      nearest_modules = find_nearest_modules_directory(module.filename)
      if nearest_modules:
        library_path = get_site_packages(os.path.join(nearest_modules, '.pip'))
        if os.path.isdir(library_path):
          library_path = normpath(library_path)
        else:
          library_path = None

    if library_path and library_path not in sys.path:
      # We can append to sys.path directly since we must be inside a
      # localimport context anyway. The localimport will also remove
      # modules imported from this path once it is exited.
      sys.path.append(library_path)
    else:
      library_path = None

    package = module.package
    if package and getattr(package, '_context_entered', 0) == 0:
      # Avoid adding the paths of the package twice.
      self._package_stack.append(package)
      package._context_entered = 1
      for path in package.vendor_directories:
        sys.path.insert(0, path)
        self.path.insert(0, path)
    elif package:
      package._context_entered += 1

    assert getattr(module, '_context_entered', 0) == 0
    module._context_entered = 1
    for path in module.vendor_directories:
      sys.path.insert(0, path)
      self.path.insert(0, path)

    self._module_stack.append(module)
    try:
      self.send_event(Context.Event_Enter, module)
      try:
        yield
      finally:
        self.send_event(Context.Event_Leave, module)
    finally:
      try:
        if self._module_stack.pop() is not module:
          raise RuntimeError('module stack corrupted')
      finally:
        if library_path:
          try:
            sys.path.remove(library_path)
          except ValueError:
            pass
        if package:
          package._context_entered -= 1
        if package and package._context_entered == 0:
          if self._package_stack.pop() is not package:
            raise RuntimeError('package stack corrupted')
          for path in package.vendor_directories:
            try:
              sys.path.remove(path)
            except ValueError:
              pass
            try:
              self.path.remove(path)
            except ValueError:
              pass
        module._context_entered -= 1
        assert module._context_entered == 0
        for path in module.vendor_directories:
          try:
            sys.path.remove(path)
          except ValueError:
            pass
          try:
            self.path.remove(path)
          except ValueError:
            pass


  def send_event(self, event_type, event_data):
    for callback in self.event_handlers:
      callback(event_type, event_data)

  def binding(self, binding_name):
    """
    Loads one of the context bindings and returns it. Bindings can be added
    to a Context using the #register_binding() method.
    """

    try:
      return self._bindings[binding_name]
    except KeyError as exc:
      raise NoSuchBindingError(binding_name)

  def register_index_file(self, filename):
    """
    Register a filename to be checked when resolving a request to a directory.
    """

    self._index_files.append(filename)

  def register_binding(self, binding_name, obj):
    """
    Registers a binding to the Context under the specified *binding_name*. The
    object can be arbitrary, but there can only be one binding under the one
    specified name at a atime. If the *binding_name* is already allocated, a
    #ValueError is raised.
    """

    if binding_name in self._bindings:
      raise ValueError('binding {!r} already exists'.format(binding_name))
    self._bindings[binding_name] = obj

  def get_loader(self, filename):
    """
    Finds the loader that can load *filename*. Depending on the loader, only
    the file extension might be enough to find an appropriate loader.
    """

    for loader in self.loaders:
      if loader.can_load(filename):
        return loader
    return None

  def get_package(self, filename, doraise=True):
    """
    Loads a `package.json` file, caches it and returns a #Package instance.
    If the *filename* does not exist and *doraise* is #False, #None will
    be returned instead of an #IOError being raised.
    """

    filename = normpath(filename)
    try:
      return self._package_cache[filename]
    except KeyError:
      pass
    try:
      with open(filename) as fp:
        manifest = json.load(fp)
    except IOError:
      if doraise: raise
      package = None
    else:
      package = Package(self, filename, json=manifest)
      self._package_cache[filename] = package

    return package

  def get_package_for(self, filename, doraise=True, maxdir=None):
    """
    Locates the nearest `package.json` for the specified *filename*.
    """

    fn = find_nearest_package_json(filename, maxdir)
    if not fn:
      return None
    return self.get_package(fn, doraise)

  def resolve(self, request):
    """
    Resolves a #Request using the registered #resolvers.
    """

    for resolver in self.resolvers:
      request.clear_state()
      try:
        return resolver.resolve(request)
      except ResolveError as exc:
        continue
    raise ResolveError(request)

  def load_module(self, loader, request, exec_=True, cache=True):
    if request.is_main and self.main_module:
      raise RuntimeError('context already has a main module')

    module = None
    from_cache = False
    filename = os.path.normpath(loader.get_filename(request))
    if cache:
      module = self._module_cache.get(filename)
      if module:
        from_cache = True

    if module is None:
      # Load the module and assert data consistency.
      module = loader.load(request)
      if not isinstance(module, BaseModule):
        raise TypeError('loader {!r} did not return a BaseModule instance, '
            'but instead a {!r} object'.format(
              type(loader).__name__, type(module).__name__))

      if request.original_resolve_location:
        # There has been at least one redirection in the filesystem when the
        # package was resolved. We will add the nearest modules directory of
        # the original resolve directory to the search path.
        # FIXME: If there are multiple package links pointing to the same
        #        package, we would actually need to load the module multiple
        #        times to ensure correct behaviour.
        nodepy_modules = find_nearest_modules_directory(request.original_resolve_location)
        if nodepy_modules:
          module.require.path.append(nodepy_modules)

    if not from_cache:
      if cache:
        self._module_cache[filename] = module
      self.send_event(Context.Event_Load, module)

    if request.is_main:
      if module.executed:
        raise RuntimeError('module already loaded, can not execute as main')
      self.main_module = module

    if module.filename != filename:
      raise RuntimeError("loaded module's filename ({}) does not match the "
          "pre-determined filename ({})".format(module.filename, filename))

    if not from_cache:
      # Invoke all extensions for the module and its owning package.
      @ExtensionHandlerRunner.wrap('module_loaded', module=module, package=module.package)
      def runner(self, handler):
        handler(module)
      runner.runall(module.extensions)
      if module.package:
        runner.runall(module.package.extensions, module.package.require)

    # Execute the module if that is requested with the load request.
    if exec_ and not module.executed:
      module.exec_()

    return module

  def resolve_and_load(self, request, current_dir=None, is_main=False,
                       path=None, additional_path=None, exec_=True, cache=True,
                       parent_module=NotImplemented):
    """
    A combination of #resolve() and #load_module() that should be used when
    actually wanting to require another module instead of just resolving a
    request or loading from a filename.
    """

    if parent_module is NotImplemented:
      parent_module = self._module_stack[-1] if self._module_stack else None

    path = list(self.path if path is None else path)
    if additional_path is not None:
      path = list(additional_path) + path

    request = Request(name=request, current_dir=current_dir,
      is_main=is_main, path=path, context=self, parent_module=parent_module)
    return self.load_module(self.resolve(request), request, exec_=exec_)


# ====================
# Helper Functions
# ====================

PackageLink = collections.namedtuple('PackageLink', 'src dst')

@contextlib.contextmanager
def post_mortem_debugger():
  """
  A context-manager that debugs the exception being raised inside the context.
  Can be disabled by setting *debug* to #False. The exception will be re-raised
  either way.
  """

  pdb.post_mortem(sys.exc_info()[2])


def get_exports(module):
  """
  Returns the `exports` member of a #BaseModule.namespace if the member exists,
  otherwise the #BaseModule.namespace is returned.
  """

  if not isinstance(module, BaseModule):
    raise TypeError('module must be a BaseModule instance')
  return getattr(module.namespace, 'exports', module.namespace)


def upiter_directory(current_dir, maxdir=None):
  """
  A helper function to iterate over the directory *current_dir* and all of
  its parent directories, excluding `nodepy_modules/` and package-scope
  directories (starting with `@`).
  """

  if maxdir:
    maxdir = os.path.abspath(maxdir)
  current_dir = os.path.abspath(current_dir)
  while True:
    dirname, base = os.path.split(current_dir)
    if not base.startswith('@') and base != 'nodepy_modules':
      yield current_dir
    if dirname == current_dir or (maxdir and dirname == maxdir):
      # Can happen on Windows for drive letters.
      break
    current_dir = dirname
  return


def find_nearest_modules_directory(current_dir, maxdir=None):
  """
  Finds the nearest `nodepy_modules/` directory to *current_dir* and returns
  it. If no such directory exists, #None is returned.
  """

  for directory in upiter_directory(current_dir, maxdir):
    result = os.path.join(directory, 'nodepy_modules')
    if os.path.isdir(result):
      return result
  return None


def find_nearest_package_json(current_file, maxdir=None):
  """
  Finds the nearest `package.json` relative to *current_file* and returns it.
  If no such file exists, #None will be returned.
  """

  for directory in upiter_directory(current_file, maxdir):
    result = os.path.join(directory, 'package.json')
    if os.path.isfile(result):
      return result
  return None


def get_package_link(current_dir):
  """
  Finds a `.nodepy-link` file in *path* or any of its parent directories,
  stopping at the first encounter of a `nodepy_modules/` directory. Returns
  a #PackageLink tuple or #None if no link was found.
  """

  for directory in upiter_directory(current_dir):
    link_file = os.path.join(directory, '.nodepy-link')
    if os.path.isfile(link_file):
      with open(link_file) as fp:
        dst = fp.read().rstrip('\n')
      return PackageLink(directory, dst)
  return None


def try_file(filename, preserve_symlinks=True):
  """
  Returns *filename* if it exists, otherwise #None.
  """

  if os.path.isfile(filename):
    if not preserve_symlinks and not is_main and os.path.islink(filename):
      return os.path.realpath(filename)
    return filename
  return None


def normpath(path, parent=None):
  if not os.path.isabs(path):
    if parent is None:
      parent = os.getcwd()
    else:
      parent = os.path.abspath(parent)
    path = os.path.join(parent, path)
  return os.path.normpath(path)


def get_site_packages(prefix):
  """
  Returns the path to the `site-packages/` directory where Python modules
  are installed to via Pip given that the specified *prefix* is the same
  that was passed during the Pip installation.
  """

  if os.name == 'nt':
    lib = 'Lib'
  else:
    lib = 'lib/python{}.{}'.format(*sys.version_info)
  return os.path.join(prefix, lib, 'site-packages')


def reload_pkg_resources(name='pkg_resources', insert_paths_index=None):
  """
  Reload the `pkg_resources` module.
  """

  if name not in sys.modules:
    return

  path = sys.path[:]

  # Reload the module. However, reloading it will fail in Python 2 if we
  # don't clear its namespace beforehand due to the way it distinguishes
  # between Python 2 and 3. We still need to keep certain members, though.
  pkg_resources = sys.modules[name]

  # Clear all members, except for special ones.
  keep = {}
  for member in ['__name__', '__loader__', '__path__']:
    if hasattr(pkg_resources, member):
      keep[member] = getattr(pkg_resources, member)
  keep.setdefault('__name__', name)
  vars(pkg_resources).clear()
  vars(pkg_resources).update(keep)

  # Keep submodules.
  for mod_name, module in six.iteritems(sys.modules):
    if mod_name.startswith(name + '.') and mod_name.count('.') == 1:
      mod_name = mod_name.split('.')[1]
      setattr(pkg_resources, mod_name, module)

  # Reload pkg_resources.
  reload(pkg_resources)

  # Reloading pkg_resources will prepend new (or sometimes already
  # existing items) in sys.path. This will give precedence to system
  # installed packages rather than local packages that we added
  # through self.importer. Thus, we shall transfer all paths that are
  # newly introduced to sys.path and skip the rest. See nodepy/nodepy#49
  for p in sys.path:
    if p not in path:
      if insert_paths_index is None:
        path.append(p)
      else:
        path.insert(insert_paths_index, p)
  sys.path[:] = path


def print_exc():
  isatty = getattr(sys.stderr, 'isatty', lambda: False)
  if isatty() and pygments:
    code = traceback.format_exc()
    lexer = pygments.lexers.PythonTracebackLexer()
    tokens = pygments.lex(code, lexer)
    formatter = pygments.formatters.TerminalFormatter()
    print(pygments.format(tokens, formatter), file=sys.stderr)
  else:
    traceback.print_exc()


def notebook_context(*args, **kwargs):
  """
  A convenience function for use inside IPython Notebooks. Creates
  a new #Context or returns an existing instance. If the function is
  called again with different arguments, the previous context will
  be destroyed and a new one will created.
  """

  import notebook
  context = getattr(notebook, '_nodepy_context', None)
  old_akw = getattr(notebook, '_nodepy_context_akw', None)
  if context is not None and old_akw != (args, kwargs):
    context.__exit__(None, None, None)
    context = None
  if context is None:
    context = Context(*args, **kwargs)
    context.__enter__()
    notebook._nodepy_context = context
    notebook._nodepy_context_akw = (args, kwargs)
  return context


# ====================
# Main
# ====================

def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument('arguments', nargs='...')
  parser.add_argument('-d', '--debug', action='store_true', default=None,
      help='Enter the interactive debugger when an exception would cause '
           'the application to exit.')
  parser.add_argument('-c', '--exec', dest='exec_', metavar='EXPR',
      help='Evaluate a Python expression.')
  parser.add_argument('--current-dir', default='.', metavar='DIR',
      help='Change where the initial request will be resolved in.')
  parser.add_argument('--version', action='store_true',
      help='Print the Node.py version and exit.')
  parser.add_argument('--keep-arg0', action='store_true',
      help='Do not overwrite sys.argv[0] when executing a file.')
  parser.add_argument('-P', '--preload', action='append', default=[])
  parser.add_argument('-L', '--loader', default=None,
      help='The loader that will be used to load and execute the module. '
           'This must be a filename that matches a loader in the Context. '
           'Usually the file suffix is sufficient (depending on the loader).')
  parser.add_argument('--pymain', action='store_true')
  parser.add_argument('--profile', type=argparse.FileType('wb'),
      help='Profile the execution and save the stats to the specified file.')
  parser.add_argument('--isolated', action='store_true',
      help='Create the runtime context in isolated mode.')
  args = parser.parse_args(sys.argv[1:] if argv is None else argv)

  if args.debug is None and os.getenv('NODEPY_DEBUG', '') == 'true':
    args.debug = True
  elif args.debug is None:
    args.debug = False

  if args.profile:
    prf = profile.Profile()
    try:
      prf.runcall(_main, args)
    finally:
      prf.create_stats()
      stats = pstats.Stats(prf)
      stats.dump_stats(args.profile.name)
      raise
  else:
    _main(args)


def _main(args):
  if args.version:
    print(VERSION)
    sys.exit(0)

  global script, proc_args, executable
  if script is None:
    executable = sys.argv[0]
    if os.name == 'nt' and not os.path.isfile(executable) \
        and not executable.endswith('.exe'):
      # For some reason on Windows in VS Code integrated terminal using
      # Git-for-Windows bash, the .exe suffix is missing..
      executable += '.exe'
    proc_args = [executable]
    if os.name == 'nt' and not executable.endswith('.exe'):
      # For example when using 'python -m nodepy', executable will point
      # to the Python source file, thus we need to execute it through the
      # Python interpreter.
      proc_args.insert(0, sys.executable)

  arguments = args.arguments[:]
  context = Context(args.current_dir, isolated=args.isolated)
  with context:
    if args.exec_ or not arguments:
      sys.argv = [sys.argv[0]] + arguments
      if args.exec_:
        exec(compile(args.exec_, '<commandline>', 'exec', dont_inherit=True), vars(context.init.namespace))
      else:
        code.interact(VERSION, local=vars(context.init.namespace))
    else:
      # A special fix for when Click is used in Python 2. A hash is generated
      # for sys.argv when Click is imported, and it gives invalid results if
      # click is imported after we modify sys.argv. Since it would be
      # inconsistent to import Click only on Windows and Python 2, we do it
      # always when possible.See https://github.com/nodepy/nodepy/issues/21 and
      # https://github.com/pallets/click/issues/751
      try:
        import click
      except ImportError:
        pass

      try:
        for request in args.preload:
          context.require(request)
        request = arguments.pop(0)
        loader = context.get_loader(args.loader) if args.loader else None
        if args.loader and loader is None:
          raise ValueError('no loader for {!r}'.format(args.loader))
        module = context.require(request, args.current_dir, is_main=True, exec_=False,
            exports=False, loader=loader)
        if args.pymain:
          module.namespace.__name__ = '__main__'
        sys.argv = [sys.argv[0] if args.keep_arg0 else module.filename] + arguments
        module.exec_()
      except SystemExit as exc:
        raise
      except BaseException as exc:
        print_exc()
        if args.debug:
          post_mortem_debugger()

  sys.exit(0)


if ('require' in globals() and require.main == module) or __name__ == '__main__':
  sys.exit(main())
