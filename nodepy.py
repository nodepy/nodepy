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
from copy import deepcopy

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.20'
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
import subprocess
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

PackageLink = collections.namedtuple('PackageLink', 'src dst')

proc_args = [sys.executable, __file__]
executable = None

if hasattr(sys, 'implementation'):
  python_impl = sys.implementation.name.lower()
else:
  python_impl = sys.subversion[0].lower()

VERSION = 'Node.py-{0} [{3} {1[0]}.{1[1]}.{1[2]} {2}-bit]'.format(
    __version__, sys.version_info, int(round(math.log(sys.maxsize, 2))) + 1,
    python_impl)


@contextlib.contextmanager
def jit_debug(debug=True):
  """
  A context-manager that debugs the exception being raised inside the context.
  Can be disabled by setting *debug* to #False. The exception will be re-raised
  either way.
  """

  try:
    yield
  except BaseException as exc:
    if debug:
      pdb.post_mortem(sys.exc_info()[2])
    raise


class NoSuchBindingError(Exception):
  pass


class ResolveError(Exception):

  def __init__(self, request, current_dir, is_main, path):
    self.request = request
    self.current_dir = current_dir
    self.is_main = is_main
    self.path = path

  def __str__(self):
    msg = "'{0}'".format(self.request)
    if self.is_main:
      msg += ' [main]'
    if self.current_dir:
      msg += " (from directory '{0}')".format(self.current_dir)
    if self.path:
      msg += ' searched in:\n  - ' + '\n  - '.join(map(repr, self.path))
    return msg


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
               parent=None, request=None, real_filename=None):
    self.context = context
    self.filename = filename
    self.real_filename = real_filename or filename
    self.directory = directory
    self.name = name
    self.namespace = types.ModuleType(str(name))  # in Python 2, does not accept Unicode
    self.require = Require(self)
    self.executed = False
    self.parent = parent
    self.request = request
    self.package = package
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

  @abc.abstractmethod
  def exec_(self):
    """
    Execute the module. If #BaseModule.executed is #True, a #RuntimeError
    should be raised. If an error occurs during the module's execution,
    #BaseModule.remove() must be called!
    """

    raise NotImplementedError


class InitModule(BaseModule):
  """
  A proxy module that is used as the entry point into Node.py modules or as
  the container for the interactive session.
  """

  def __init__(self, context):
    super(InitModule, self).__init__(context, '__init__', context.current_dir, '__init__')

  def exec_(self):
    raise RuntimeError('can not exec InitModule')


class PythonModule(BaseModule):
  """
  Represents a Node.py Python module object that is executed from a code
  object. The #PythonLoader is responsible for loading the code from files
  respectively.
  """

  def __init__(self, context, filename, real_filename, name, code,
               package, parent, request):
    super(PythonModule, self).__init__(
        context=context, filename=filename, package=package,
        directory=os.path.dirname(filename), name=name, parent=parent,
        request=request)
    self.code = code
    self.real_filename = real_filename

  def exec_(self):
    if self.executed:
      raise RuntimeError('already executed')
    try:
      self.executed = True
      with self.context.enter_module(self):
        exec(self.code, vars(self.namespace))
    except:
      self.remove()
      raise


class BaseLoader(six.with_metaclass(abc.ABCMeta)):
  """
  Interface for loader objects.
  """

  @abc.abstractmethod
  def suggest_try_files(self, filename):
    return; yield

  @abc.abstractmethod
  def can_load(self, filename):
    return False

  @abc.abstractmethod
  def load(self, context, filename, request, parent, package):
    return BaseModule()


class PythonLoader(BaseLoader):
  """
  A loader for nodepy Python modules.

  # Parameters
  write_bytecache (bool, None): Write bytecache files. If not specified,
      checks the `PYTHONDONTWRITEBYTECODE` environment variable.
  """

  # Choose an implementation and version dependent suffix for Python
  # bytecache files.
  pyc_suffix = '.{}-{}{}.pyc'.format(python_impl.lower(), *sys.version_info)

  def __init__(self, write_bytecache=None):
    if write_bytecache is None:
      write_bytecache = not bool(os.getenv('PYTHONDONTWRITEBYTECODE', '').strip())
    self.write_bytecache = write_bytecache

  def suggest_try_files(self, filename):
    yield filename + '.py'
    yield filename + self.pyc_suffix

  def can_load(self, filename):
    return filename.endswith('.py') or filename.endswith(self.pyc_suffix)

  def load(self, context, filename, request, parent, package):
    """
    Called when a #Context requires to load a module for a filename. The
    #PythonLoader will always check if a byte-compiled version of the source
    file already exists and if the respective source file has not been modified
    since it was created.
    """

    filename_noext = os.path.splitext(filename)[0]
    name = os.path.basename(filename_noext)
    bytecache_file = filename_noext + self.pyc_suffix

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
              tmp.write(self._preprocess(package, filename, src.read()))
            tmp.close()
            py_compile.compile(tmp.name, bytecache_file, doraise=True)
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
      code = self.load_code(package, bytecache_file, is_compiled=True)
      real_filename = bytecache_file
    else:
      code = self.load_code(package, filename, is_compiled=None)
      real_filename = None

    return PythonModule(context=context, filename=filename, name=name,
        code=code, parent=parent, request=request, real_filename=real_filename,
        package=package)

  def _preprocess(self, package, filename, source):
    for ext in (package.get_extensions() if package else []):
      if hasattr(ext, 'preprocess_python_source'):
        source = ext.preprocess_python_source(package, filename, source)
    return source

  def load_code(self, package, filename, is_compiled=None):
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
        return marshal.load(fp)
    else:
      with open(filename, 'r') as fp:
        source = self._preprocess(package, filename, fp.read())
        return compile(source, filename, 'exec', dont_inherit=True)


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
      left = name
      if 'as' in name:
        name, __, left = name.partition('as')
      stmt += '{0}=_reqres.{1};'.format(left.strip(), name.strip())
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
  """

  _re_import_as = re.compile(
    r'''^(?P<indent>[^\S\n]*)import\s+(?P<q>"|')(?P<mod>.*?)(?P=q)(?:\s+as\s+(?P<n>\w+))?[^\S\n]*$''',
    re.M
  )
  _re_import_from = re.compile(
    r'''^(?P<indent>[^\S\n]*)import\s+(?P<members>(?:\w+|(?:\w+\s*,\s*)?\{[^}]+\}))\s+from\s+(?P<q>["'])(?P<mod>.*)(?P=q)[^\S\n]*$''',
    re.M
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
          repl = '{} = require({!r})'.format(as_name, match.group('mod'))
        else:
          repl = 'require({!r})'.format(match.group('mod'))
      elif kind == 'from':
        module = match.group('mod')
        members = match.group('members')
        if '{' in members:
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
        else:
          repl = '{} = require({!r})'.format(members, module)
      else:
        raise RuntimeError

      # Add additional newlines to the replacement until it spans
      # the same number of newlines than the matched sequence. This
      # is to keep error message more consistent.
      repl = match.group('indent') + repl + '\n' * match.group(0).count('\n')

      source = source[:match.start()] + repl + source[match.end():]

    return source


class JsonLoader(object):
  """
  Loader for `.json` files.
  """

  def __init__(self, suggest_json_suffix=False):
    self.suggest_json_suffix = suggest_json_suffix

  def suggest_try_files(self, filename):
    if self.suggest_json_suffix:
      yield filename + '.json'

  def can_load(self, filename):
    return filename.endswith('.json')

  def load(self, context, filename, request, parent, package):
    if os.path.basename(filename) == 'package.json':
      assert isinstance(package, Package), package
      assert os.path.normpath(os.path.abspath(filename)) == \
        os.path.normpath(os.path.abspath(filename))
      return package.module
    return JsonModule(context, filename, request=request, parent=parent,
      package=package)


class JsonModule(BaseModule):

  def __init__(self, context, filename, parent=None, request=None, package=None):
    directory, name = os.path.split(filename)
    super(JsonModule, self).__init__(
      context=context, filename=filename, directory=directory, name=name,
      parent=parent, request=request, package=package)

  def exec_(self):
    if self.executed:
      raise RuntimeError('already loaded')
    if os.path.basename(self.filename) == 'package.json' and self.package:
      self.namespace.exports = self.package.json
    else:
      with open(self.filename, 'r') as fp:
        self.namespace.exports = json.load(fp)


class Require(object):
  """
  The `require()` function for #PythonModule#s.
  """

  NoSuchBindingError = NoSuchBindingError
  ResolveError = ResolveError
  PY2 = six.PY2
  PY3 = six.PY3

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
      return self.context.binding(request[1:])

    if cache and request in self.cache:
      module = self.cache[request]
    else:
      current_dir = current_dir or self.module.directory
      self.context.send_event('require', {
          'request': request, 'current_dir': current_dir,
          'is_main': is_main, 'cache': cache, 'parent': self.module}
      )
      module = self.context.resolve_and_load(request, current_dir,
          is_main=is_main, additional_path=self.path, cache=cache,
          parent=self.module, exec_=exec_, loader=loader)
      if cache:
        self.cache[request] = module
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
                exec_=True, exports=True):
    """
    Uses #hide_main() to temporarily swap out the current main module and
    loading another module as main. Returns the loaded module.
    """

    with self.hide_main(argv=argv):
      return self(request, current_dir, is_main=True, cache=cache,
                  exec_=exec_, exports=exports)

  def subprocess(self, request, args=(), nodepy_args=(), **kwargs):
    """
    Resolves *request* and executes it as a subprocess. Returns the created
    subprocess.
    """

    cmd = self.subprocess_args(request, args, nodepy_args)
    return subprocess.Popen(cmd, **kwargs)

  def subprocess_args(self, request, args=(), nodepy_args=()):
    """
    Resolves *request* and returns the argument list that would be used to
    execute it as a subprocess.
    """

    filename = self.context.resolve(request, self.module.directory)
    return proc_args + list(nodepy_args) + [filename] + list(args)


def get_exports(module):
  """
  Returns the `exports` member of a #BaseModule.namespace if the member exists,
  otherwise the #BaseModule.namespace is returned.
  """

  if not isinstance(module, BaseModule):
    raise TypeError('module must be a BaseModule instance')
  return getattr(module.namespace, 'exports', module.namespace)


def upiter_directory(current_dir):
  """
  A helper function to iterate over the directory *current_dir* and all of
  its parent directories, excluding `nodepy_modules/` and package-scope
  directories (starting with `@`).
  """

  current_dir = os.path.abspath(current_dir)
  while True:
    dirname, base = os.path.split(current_dir)
    if not base.startswith('@') and base != 'nodepy_modules':
      yield current_dir
    if dirname == current_dir:
      # Can happen on Windows for drive letters.
      break
    current_dir = dirname
  return


def find_nearest_modules_directory(current_dir):
  """
  Finds the nearest `nodepy_modules/` directory to *current_dir* and returns
  it. If no such directory exists, #None is returned.
  """

  for directory in upiter_directory(current_dir):
    result = os.path.join(directory, 'nodepy_modules')
    if os.path.isdir(result):
      return result
  return None


def find_nearest_package_json(current_file):
  """
  Finds the nearest `package.json` relative to *current_file* and returns it.
  If no such file exists, #None will be returned.
  """

  for directory in upiter_directory(current_file):
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
    self._extensions = None

  def __repr__(self):
    return "<Package '{}@{}' at '{}'>".format(
      self.json.get('name'), self.json.get('version'), self.filename)

  @property
  def directory(self):
    return os.path.dirname(filename)

  def get_extensions(self):
    if self._extensions is not None:
      return self._extensions
    self._extensions = []
    for request in self.json.get('extensions', []):
      ext = self.module.require(request)
      if hasattr(ext, 'init_extension'):
        ext.init_extension(self)
      self._extensions.append(ext)
    return self._extensions


class Context(object):
  """
  The context encapsulates the execution of Python modules. It serves as the
  central unit to control the finding, caching and loading of Python modules.
  """

  def __init__(self, current_dir='.', bare=False, isolated=True):
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
    # Loaders for files that can be required.
    self.loaders = []
    # A list of functions that are called for various events. The first
    # arugment is always the event type, followed by the event data.
    self.event_handlers = []
    # A list of additional search directories. Defaults to the paths specified
    # in the `NODEPY_PATH` environment variable.
    self.path = list(filter(bool, os.getenv('NODEPY_PATH', '').split(os.pathsep)))
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
      self.loaders.append(PythonLoader())
      self.loaders.append(JsonLoader())
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
    if 'pkg_resources' in sys.modules:
      reload(sys.modules['pkg_resources'])
    return self

  def __exit__(self, *args):
    if self.isolated:
      try:
        return self.importer.__exit__(*args)
      finally:
        if 'pkg_resources' in sys.modules:
          reload(sys.modules['pkg_resources'])

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
          library_path = os.path.normpath(library_path)
        else:
          library_path = None

    if library_path and library_path not in sys.path:
      # We can append to sys.path directly since we must be inside a
      # localimport context anyway. The localimport will also remove
      # modules imported from this path once it is exited.
      sys.path.append(library_path)
    else:
      library_path = None

    self._module_stack.append(module)
    try:
      self.send_event('enter', module)
      yield
    finally:
      try:
        if self._module_stack.pop() is not module:
          raise RuntimeError('module stack corrupted')
      finally:
        if library_path:
          sys.path.remove(library_path)

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

  def _get_package_main(self, dirname):
    """
    Checks if there exists a `package.json` in the specified *dirname*, loads
    it and then returns the value of its `"main"` field. If the field or the
    manifest does not exist, #None is returned.
    """

    fn = os.path.abspath(os.path.join(dirname, 'package.json'))
    package = self._get_package(fn, doraise=False)
    if package:
      main = package.json.get('main')
      if main: main = str(main)
      return main
    else:
      return None

  def _get_package(self, filename, doraise=True):
    """
    Loads a `package.json` file, caches it and returns a #Package instance.
    If the *filename* does not exist and *doraise* is #False, #None will
    be returned instead of an #IOError being raised.
    """

    filename = os.path.normpath(filename)
    try:
      return self._package_cache[filename]
    except KeyError:
      pass
    try:
      with open(filename) as fp:
        manifest = json.load(fp)
    except IOError:
      self._package_cache[filename] = None
      if doraise: raise
      package = None
    else:
      package = Package(self, filename, json=manifest)
      self._package_cache[filename] = package

    return package

  def resolve(self, request, current_dir=None, is_main=False, path=None,
              followed_from=None):
    """
    Resolves the *request* to a filename of a module that can be loaded by one
    of the extension loaders. For relative requests (ones starting with `./` or
    `../`), the *current_dir* will be used to generate an absolute request.
    Absolute requests will then be resolved by using #try_file() and the
    suggested files returned by #BaseLoader.suggest_try_files().

    Dependency requests are those that are neither relative nor absolute and
    are of the format `[@<scope>]<name>[/<module>]`. Such requests are looked
    up in the nearest `nodepy_modules/` directory of the *current_dir* and
    then alternatively in the specified list of directories specified with
    *path*. If *path* is #None, it defaults to the #Context.path.

    If *is_main* is specified, dependency requests are also looked up like
    relative requests before the normal lookup procedure kicks in.

    Raises a #ResolveError if the *request* could not be resolved into a
    filename.
    """

    if request in '..' or request.startswith('./') or request.startswith('../'):
      try:
        return self.resolve(os.path.abspath(os.path.join(current_dir, request)))
      except ResolveError as exc:
        raise ResolveError(request, current_dir, is_main, path)
    elif os.path.isabs(request):
      link = get_package_link(request)
      if link:
        request = os.path.join(link.dst, os.path.relpath(request, link.src))
        if followed_from is not None:
          followed_from.append(link)
      filename = try_file(request)
      if filename:
        return filename
      for loader in self.loaders:
        for filename in loader.suggest_try_files(request):
          filename = try_file(filename)
          if filename: return filename
      if os.path.isdir(request):
        # If there is a package.json file in this directory, we can parse
        # it for its "main" field to find the file we should be requiring
        # for this directory.
        main = self._get_package_main(request)
        if main:
          return self.resolve(os.path.join(request, main), current_dir, is_main, path)
        else:
          # Otherwise, try the standard index files.
          for choice in self._index_files:
            new_request = os.path.join(request, choice)
            try:
              return self.resolve(new_request, current_dir, is_main, path)
            except ResolveError:
              continue
      raise ResolveError(request, current_dir, is_main, path)

    if current_dir is None and is_main:
      current_dir = '.'

    path = list(self.path if path is None else path)
    nodepy_modules = find_nearest_modules_directory(current_dir)
    if nodepy_modules:
      path.insert(0, nodepy_modules)
    if is_main:
      path.insert(0, current_dir)

    for directory in path:
      new_request = os.path.join(os.path.abspath(directory), request)
      try:
        return self.resolve(new_request, None)
      except ResolveError:
        pass

    raise ResolveError(request, current_dir, is_main, path)

  def load_module(self, filename, is_main=False, exec_=True, cache=True,
                  loader=None, followed_from=None, request=None, parent=None):
    """
    Loads a module by *filename*. The filename will be converted to an
    absolute path and normalized. If the module is already loaded, the
    cached module will be returned.

    Note that the returned #BaseModule will be ensured to be executed
    unless *exec_* is set to False.

    In order to keep the correct reference directory when loading files via
    package links (directories that contain a `.nodepy-link` file), the
    *follow_from* argument should be specified which must be a list which
    was obtained via #resolve()'s same parameter. It must be a list of
    #PackageLink objects.
    """

    if is_main and self.main_module:
      raise RuntimeError('context already has a main module')

    filename = os.path.normpath(os.path.abspath(filename))
    if cache and filename in self._module_cache:
      return self._module_cache[filename]

    if loader is None:
      for loader in self.loaders:
        if loader.can_load(filename):
          break
      else:
        raise ValueError('no loader for {!r}'.format(filename))

    # Find the nearest package for the module.
    pfn = find_nearest_package_json(filename)
    package = self._get_package(pfn) if pfn else None

    module = loader.load(self, filename, request, parent, package)
    if not isinstance(module, BaseModule):
      raise TypeError('loader {!r} did not return a BaseModule instance, '
          'but instead a {!r} object'.format(
            type(loader).__name__, type(module).__name__))
    if module.filename != filename:
      raise RuntimeError("loaded module's filename does not match the "
          "filename passed to the loader ({})".format(
              getattr(loader, "__name__", None) or type(loader).__name__))

    for ext in (package.get_extensions() if package else []):
      if hasattr(ext, 'module_loaded'):
        ext.module_loaded(module)

    if followed_from:
      nodepy_modules = find_nearest_modules_directory(followed_from[0].src)
      if nodepy_modules:
        module.require.path.append(nodepy_modules)
    if cache:
      self._module_cache[filename] = module
    if is_main:
      self.main_module = module

    self.send_event('load', module)
    if exec_ and not module.executed:
      module.exec_()
    return module

  def resolve_and_load(self, request, current_dir=None, is_main=False,
                       path=None, additional_path=None, frollowed_from=None,
                       exec_=True, cache=True, loader=None, parent=NotImplemented):
    """
    A combination of #resolve() and #load_module() that should be used when
    actually wanting to require another module instead of just resolving a
    request or loading from a filename.
    """

    if parent is NotImplemented:
      parent = self._module_stack[-1] if self._module_stack else None

    path = list(self.path if path is None else path)
    if additional_path is not None:
      path = list(additional_path) + path
    followed_from = []
    filename = self.resolve(request, current_dir, is_main=is_main,
        path=path, followed_from=followed_from)
    return self.load_module(filename, is_main=is_main, cache=cache,
        exec_=exec_, loader=loader, followed_from=followed_from,
        request=request, parent=parent)


def print_exc():
  if sys.stderr.isatty() and pygments:
    code = traceback.format_exc()
    lexer = pygments.lexers.PythonTracebackLexer()
    tokens = pygments.lex(code, lexer)
    formatter = pygments.formatters.TerminalFormatter()
    print(pygments.format(tokens, formatter), file=sys.stderr)
  else:
    traceback.print_exc()


def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument('arguments', nargs='...')
  parser.add_argument('-d', '--debug', action='store_true',
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

  global proc_args, executable
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
  with context, jit_debug(args.debug):
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

  sys.exit(0)


if ('require' in globals() and require.main == module) or __name__ == '__main__':
  sys.exit(main())
