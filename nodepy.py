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
Node.py is a loader for Python modules in the Node.js-style. Unlike standard
Python modules, the Node.py `require()` caches modules by their filename and
thus allows modules with the same name be loaded from multiple locations at
the same time.
"""

from __future__ import absolute_import, division, print_function

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.9'
__license__ = 'MIT'

import code
import contextlib
import itertools
import os
import pdb
import sys
import traceback
import types

import click
import localimport
import six

VERSION = 'Node.py-{0} [Python {1}.{2}.{3}]'.format(__version__, *sys.version_info)


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


def _get_name(x):
  if hasattr(x, '__name__'):
    return x.__name__
  return type(x).__name__


def new_module(name):
  """
  Creates a new #types.ModuleType object from the specified *name*. In Python
  2, the constructor accepts only normal strings and not unicode (which is what
  we get from #click though).
  """

  if six.PY2 and isinstance(name, unicode):
    name = name.encode()
  return types.ModuleType(name)


class ResolveError(Exception):
  def __init__(self, request, current_dir, is_main, path):
    self.request = request
    self.current_dir = current_dir
    self.is_main = is_main
    self.path = path


class UnknownModuleTypeError(Exception):
  def __filename__(self, filename):
    self.filename = filename


class BaseModule(object):
  """
  Represents a Python module that exposes members like data, functions and
  classes in its #namespace.
  """

  def __init__(self, context, filename, directory, name):
    self.context = context
    self.filename = filename
    self.directory = directory
    self.name = name
    self.namespace = new_module(name)
    self.executed = False
    self.init_namespace()

  def init_namespace(self):
    self.namespace.__file__ = self.filename
    self.namespace.__name__ = self.name
    self.namespace.require = Require(self)
    self.namespace.module = self
    if self.directory:
      self.namespace.__directory__ = self.directory

  def exec_(self):
    raise NotImplementedError


class InteractiveSessionModule(BaseModule):
  """
  A proxy module used for interactive sessions.
  """

  def __init__(self, context):
    super(InteractiveSessionModule, self).__init__(context, '__interactive__',
        os.getcwd(), 'interactive')


class NodepyModule(BaseModule):
  """
  Represents an actual `.py` file.
  """

  def __init__(self, context, filename):
    dirname, base = os.path.split(filename)
    super(NodepyModule, self).__init__(context, filename,
        dirname, os.path.splitext(base)[0])

  def exec_(self):
    if self.executed:
      raise RuntimeError('already executed')
    self.executed = True
    with open(self.filename, 'r') as fp:
      code = fp.read()
    with self.context.enter_module(self):
      exec(compile(code, self.filename, 'exec'), vars(self.namespace))


class Require(object):
  """
  The `require()` function for #NodepyModule#s.
  """

  def __init__(self, module):
    self.module = module

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

  def __call__(self, request):
    current_dir = self.module.directory
    filename = self.context.resolve(request, current_dir)
    module = self.context.load_module(filename)
    return get_exports(module)


def get_exports(module):
  """
  Returns the `exports` member of a #BaseModule.namespace if the member exists,
  otherwise the #BaseModule.namespace is returned.
  """

  if not isinstance(module, BaseModule):
    raise TypeError('module must be a BaseModule instance')
  return getattr(module.namespace, 'exports', module.namespace)


def find_nearest_modules_directory(current_dir):
  """
  Finds the nearest `nodepy_modules/` directory to *current_dir* and returns
  it. If no such directory exists, #None is returned.
  """

  while True:
    dirname, base = os.path.split(current_dir)
    if not base.startswith('@') and base != 'nodepy_modules':
      # Avoid returning paths like `nodepy_modules/nodepy_modules` and
      # paths inside a scoped package.
      result = os.path.join(current_dir, 'nodepy_modules')
      if os.path.isdir(result):
        return result
    if dirname == current_dir:
      # Can happen on Windows for drive letters.
      break
    current_dir = dirname
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


class Context(object):
  """
  The context encapsulates the execution of Python modules. It serves as the
  central unit to control the finding, caching and loading of Python modules.
  """

  def __init__(self, current_dir='.'):
    # Container for internal modules that can be bound to the context
    # explicitly with the #register_binding() method.
    self._bindings = {}
    # Loaders for file extensions. The default loader for `.py` files is
    # automatically registered.
    self._extensions = {}
    self.register_extension('.py', NodepyModule)
    # Container for cached modules. The keys are the absolute and normalized
    # filenames of the module so that the same file will not be loaded multiple
    # times.
    self._module_cache = {}
    # A stack of modules that are currently being executed. Every module
    # should add itself on the stack when it is executed with #enter_module().
    self._module_stack = []
    # A list of additional search directories. Defaults to the paths specified
    # in the `NODEPY_PATH` environment variable.
    self.path = list(filter(bool, os.getenv('NODEPY_PATH', '').split(os.pathsep)))
    # The main module. Will be set by #load_module().
    self.main_module = None
    # Localimport context for .pymodules installed by PPYM.
    self.importer = localimport.localimport([
        os.path.join(current_dir, 'nodepy_modules/.pymodules')], '.')

  def __enter__(self):
    self.importer.__enter__()

  def __exit__(self, *args):
    return self.importer.__exit__(*args)

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
    self._module_stack.append(module)
    try:
      yield
    finally:
      if self._module_stack.pop() is not module:
        raise RuntimeError('module stack corrupted')

  def binding(self, binding_name):
    """
    Loads one of the context bindings and returns it. Bindings can be added
    to a Context using the #register_binding() method.
    """

    return get_exports(self._bindings[binding_name])

  def register_binding(self, binding_name, module):
    """
    Registers a binding to the Context under the specified *binding_name*. The
    *module* must be a #BaseModule instance. If a binding with the specified
    name already exists, a #ValueError is raised.
    """

    if not isinstance(module, BaseModule):
      raise TypeError('module must be a BaseModule instance')
    if binding_name in self._bindings:
      raise ValueError('binding {!r} already exists'.format(binding_name))
    self._bindings[binding_name] = module

  def register_extension(self, ext, loader):
    """
    Registers a loader function for the file extension *ext*. The dot should
    be included in the *ext*. *loader* must be a callable that expects the
    Context as its first and the filename to load as its second argument.

    If a loader for *ext* is already registered, a #ValueError is raised.
    """

    if ext in self._extensions:
      raise ValueError('extension {!r} already registered'.format(ext))
    if not callable(loader):
      raise TypeError('loader must be a callable')
    self._extensions[ext] = loader

  def resolve(self, request, current_dir=None, is_main=False, path=None):
    """
    Resolves the *request* to a filename of a module that can be loaded by one
    of the extension loaders. For relative requests (ones starting with `./` or
    `../`), the *current_dir* will be used to generate an absolute request.
    Absolute requests will then be resolved by using #try_file() and the
    extensions that have been registered with #register_extension().

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

    if request.startswith('./') or request.startswith('../'):
      try:
        return self.resolve(os.path.abspath(os.path.join(current_dir, request)))
      except ResolveError as exc:
        raise ResolveError(request, current_dir, is_main, path)
    elif os.path.isabs(request):
      # TODO: Support links to packages by a special link file for
      #       develop installations.
      # TODO: Extension order by priority.
      filename = try_file(request)
      if filename:
        return filename
      for ext in self._extensions:
        filename = try_file(request + ext)
        if filename:
          return filename
      if os.path.isdir(request):
        request = os.path.join(request, 'index')
        return self.resolve(request, current_dir, is_main, path)
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

  def load_module(self, filename, is_main=False, exec_=True):
    """
    Loads a module by *filename*. The filename will be converted to an
    absolute path and normalized. If the module is already loaded, the
    cached module will be returned.

    Note that the returned #BaseModule will be ensured to be executed
    unless *exec_* is set to False.
    """

    if is_main and self.main_module:
      raise RuntimeError('context already has a main module')

    filename = os.path.normpath(os.path.abspath(filename))
    if filename in self._module_cache:
      return self._module_cache[filename]
    for ext, loader in six.iteritems(self._extensions):
      if filename.endswith(ext):
        break
    else:
      raise UnknownModuleTypeError(filename)
    module = loader(self, filename)
    if not isinstance(module, BaseModule):
      raise TypeError('loader {!r} did not return a BaseModule instance, '
          'but instead a {!r} object'.format(_get_name(loader), _get_name(module)))
    assert module.filename == filename
    self._module_cache[filename] = module
    if is_main:
      self.main_module = module
    if exec_ and not module.executed:
      module.exec_()
    return module


@click.command(help=__doc__, context_settings={'ignore_unknown_options': True})
@click.argument('arguments', nargs=-1, type=click.UNPROCESSED)
@click.option('-d', '--debug', is_flag=True,
    help='Enter the interactive debugger on exception.')
@click.option('-v', '--version', is_flag=True,
    help='Print the Node.py version and exit.')
@click.option('-c', '--exec', 'exec_string', metavar='EXPRESSION',
    help='Evaluate an expression.')
@click.option('--current-dir', default='.',
    help='Change where <request> will be resolved.')
def main(arguments, debug, version, exec_string, current_dir):
  if version:
    print(VERSION)
    sys.exit(0)

  arguments = list(arguments)
  context = Context(current_dir)
  with context, jit_debug(debug):
    if exec_string or not arguments:
      sys.argv = [sys.argv[0]] + arguments
      module = InteractiveSessionModule(context)
      if exec_string:
        exec(exec_string, vars(module.namespace))
      else:
        code.interact(VERSION, local=vars(module.namespace))
    else:
      request = arguments.pop(0)
      filename = context.resolve(request, current_dir, is_main=True)
      sys.argv = [filename] + list(arguments)
      module = context.load_module(filename, is_main=True)

  sys.exit(0)


if ('require' in globals() and require.main == module) or __name__ == '__main__':
  main()
