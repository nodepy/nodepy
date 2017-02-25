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

import collections
import contextlib
import itertools
import localimport
import os
import types

from .config import Config

PYMODULES = '.pymodules'
PPY_MODULES = 'ppy_modules'
PACKAGE_JSON = 'package.json'


class ResolveError(Exception):
  """
  Raised when a module name could not be resolved.
  """

  def __init__(self, request, current_dir, path):
    self.request = request
    self.current_dir = current_dir
    self.path = path

  def __str__(self):
    msg = 'Cannot find module \'{}\''.format(self.request)
    if self.current_dir:
      msg += '\n  From \'{}\''.format(self.current_dir)
    if self.path:
      msg += '\n  In  - ' + '\n      - '.join(self.path)
    return msg


class Session(object):
  """
  A session represents a complete and isolated ppy environment. Note that for
  ppy to function, the following ppy modules must always be present:

  - @ppym/argschema (a dependency of @ppym/semver)
  - @ppym/semver (a dependency of @ppym/manifest)
  - @ppym/manifest

  When installing ppy via Pip, these and @ppym/ppym will be automatically
  installed into the global modules directory from the versions contained
  as Git submodules.

  For a development install of ppy, they will be automatically loade from
  the development directorie's `ppy_modules/` directory.

  The #Session has a global #Require instance that is used to bootstrap these
  modules when they are needed. Currently, only #Session.get_manifest() needs
  to bootstrap the @ppym/manifest module. #Session._require will be initialized
  once the session context is entered with #Session.__enter__().
  """

  def __init__(self, config=None):
    self.config = config = config or Config()
    self.path = [get_bootstrap_modules_dir(config)]
    self.main_module = None
    self.module_cache = {}
    self.manifest_cache = {}
    self.current_modules = collections.deque()
    self.preserve_symlinks = config.get('preserve_symlinks') == 'true'

    # Import context for Python modules.
    self.localimport = localimport.localimport([PPY_MODULES + '/' + PYMODULES], '.')

    prefix = config.get('prefix')
    if prefix:
      self.add_path(os.path.join(prefix, PPY_MODULES))
    self.add_path(*filter(bool, config.get('path', '').split(os.pathsep)))
    self.add_path(*filter(bool, os.environ.get('PPY_PATH', '').split(os.pathsep)))

    # Some code, like the `PackageManifest` class, is contained in the
    # @ppym/manifest package and must be bootstrap-loaded. This member
    # will be initialized to a dictionary with bootstrapped members, like
    # the `PackageManifest` class.
    self._require = None

  def __enter__(self):
    self.localimport.__enter__()
    self.bootstrap()
    return self

  def __exit__(self, *args):
    self.localimport.__exit__(*args)

  @contextlib.contextmanager
  def enter_module(self, module):
    assert isinstance(module, Module)
    self.current_modules.append(module)
    try:
      yield
    finally:
      assert self.current_modules.pop() is module

  def add_path(self, *path):
    for p in path:
      self.path.append(p)
      x = os.path.join(p, PYMODULES)
      self.localimport.path.append(x)

  def bootstrap(self):
    if self._require is None:
      self._require = Require(None, self, is_bootstrap=True)
    self._require('@ppym/manifest')

  def get_manifest(self, filename):
    """
    Parses a #PackageManifest from *filename* and returns it. The manifest
    is cached by the absolute and normalized *filename*.
    """

    if not self._require:
      raise RuntimeError('Session is not bootstrapped')

    filename = canonicalpath(filename)
    if filename in self.manifest_cache:
      return self.manifest_cache[filename]
    manifest = self._require('@ppym/manifest').parse(filename)
    self.manifest_cache[filename] = manifest
    return manifest

  def get_module(self, filename):
    """
    Returns a #Module from the specified *filename*. If the module is not
    already cached, it will be created. Note that the module is not necessarily
    loaded. You can do that with #Module.load().

    Requires the session to be bootstrapped, that is #Session.bootstrap()
    must have been called or #Session.__enter__() be used.
    """

    filename = canonicalpath(filename)
    if filename in self.module_cache:
      return self.module_cache[filename]

    module = Module(filename, self)
    self.module_cache[filename] = module
    return module

  def resolve(self, request, current_dir=None, is_main=False, path=None):
    """
    Uses #resolve_module_filename() and raises #ResolveError if the *request*
    could not be resolved. Returns a #Module object. If *is_main* is #True,
    the #Session.main_module will be set. Note that if #Session.main_module
    is already set, a #RuntimeError will be raised if *is_main* is #True.
    """

    if is_main and self.main_module:
      raise RuntimeError('already have a main module')

    current_dir = current_dir or os.getcwd()
    if path is None:
      path = list(iter_module_paths(current_dir, is_main)) + self.path

    filename = self.resolve_module_filename(request, current_dir, is_main, path)
    if not filename:
      raise ResolveError(request, current_dir, path)

    module = self.get_module(filename)
    if is_main:
      self.main_module = module
    return module

  def resolve_module_filename(self, request, current_dir, is_main, path, is_bootstrap=False):
    """
    Resolves the filename for a Python module from the specified *request*
    name. This may be a relative name like `./path/to/module` in which case
    it is evaluated solely in *current_dir*. Otherwise, if the requested module
    is in standard format (eg. `module-name/core`), the module name is resolved
    in the specified *path*.

    If no file can be found, #None is returned.
    """

    def try_file_(filename):
      return try_file(filename, self.preserve_symlinks and not is_main)

    def try_abs_(request):
      if os.path.isdir(request):
        # We can only load a manifest once we bootstrapped the @ppym/manifest
        # package.
        mffile = os.path.join(request, PACKAGE_JSON)
        if is_bootstrap or not os.path.isfile(mffile):
          main = 'index'
        else:
          assert '@ppym/manifest' in self._require.cache
          main = self.get_manifest(mffile).main
        filename = try_abs_(os.path.join(request, main))
      else:
        filename = try_file_(request)
      return filename or try_file_(request + '.py')

    if os.path.isabs(request):
      return try_abs_(request)

    current_dir = current_dir or os.getcwd()
    if ispurerelative(request):
      filename = os.path.normpath(os.path.join(current_dir, request))
      return self.resolve_module_filename(filename, current_dir, is_main, path, is_bootstrap)

    for directory in path:
      if not os.path.isdir(directory):
        continue
      filename = canonicalpath(os.path.join(directory, request))
      filename = self.resolve_module_filename(filename, current_dir, is_main, path, is_bootstrap)
      if filename:
        return filename


class Module(object):
  """
  Represents a ppy Python module.
  """

  def __init__(self, filename, session, is_bootstrap=False):
    self.filename = filename
    self.directory = os.path.dirname(filename)
    self.namespace = types.ModuleType(filename)
    self.is_bootstrap = is_bootstrap
    self.session = session
    self.loaded = False

  def __repr__(self):
    return '<Module {!r}>'.format(self.filename)

  def load(self):
    if self.loaded:
      raise RuntimeError('module already loaded')
    self.loaded = True

    # Initialize the module's namespace.
    vars(self.namespace).update({
      '_filename': self.filename,
      '_dirname': self.directory,
      'require': Require(self, is_bootstrap=self.is_bootstrap)
    })

    with self.session.enter_module(self):
      with open(self.filename, 'r') as fp:
        code = fp.read()
      code = compile(code, self.filename, 'exec')
      exec(code, vars(self.namespace))


class Require(object):
  """
  Implements the `require()` function. An object of this class is created
  separately for every #Module.
  """

  ResolveError = ResolveError

  def __init__(self, module, session=None, directory=None, is_bootstrap=False):
    self.module = module
    self.session = session or module.session
    self.directory = directory or (module.directory if module else None)
    self.path = []
    if self.directory:
      self.path.extend(iter_module_paths(self.directory, self.is_main))
    self.path.extend(self.session.path)
    self.is_bootstrap = is_bootstrap
    self.cache = {}

  def __repr__(self):
    return '<Require of {!r}>'.format(self.module)

  def __call__(self, name):
    if name in self.cache:
      return self.cache[name]
    module = self.session.get_module(self.resolve(name))
    module.is_bootstrap = self.is_bootstrap
    if not module.loaded:
      module.load()
    result = module.namespace
    if hasattr(result, 'exports'):
      result = result.exports
    self.cache[name] = result
    return result

  def resolve(self, name):
    filename = self.session.resolve_module_filename(name, self.directory,
        is_main=False, path=self.path, is_bootstrap=self.is_bootstrap)
    if not filename:
      raise ResolveError(name, self.directory, self.path)
    return filename

  @property
  def is_main(self):
    return self.module is self.main

  @property
  def main(self):
    return self.session.main_module


def iter_module_paths(from_dir, is_main=False):
  """
  Yield all possible `ppy_modules/` paths that can be matched starting from
  *from_dir*. Note that the method can yield directories that don't exist.
  """

  if is_main:
    yield '.'
  from_dir = canonicalpath(from_dir)
  while from_dir:
    dirname, base = os.path.split(from_dir)
    if base != PPY_MODULES and not base.startswith('@'):
      # Avoid yielding paths like `ppy_modules/ppy_modules`.
      yield os.path.join(from_dir, 'ppy_modules')
    if from_dir == dirname:
      # If we hit a drive letter on Windows.
      break
    from_dir = dirname

  if os.name != 'nt':
    # TODO: Node does this, but I'm not sure if we need that with our
    # current implementation of this method.
    yield '/node_modules'


def try_file(filename, preserve_symlinks, is_main=False):
  """
  Returns *filename* if it exists. If *is_main* is #False and
  `--preserve-symlinks`, symlinks will be kept intact.
  """

  if os.path.isfile(filename):
    if not preserve_symlinks and not is_main and os.path.islink(filename):
      return os.path.realpath(filename)
    return filename
  return None


def ispurerelative(path):
  """
  Returns #True if *path* is a purely relative filename, that is if it begins
  with `./` or `../`. Returns #False otherwise.
  """

  return path.startswith('./') or path.startswith('../')


def canonicalpath(path):
  """
  Makes *path* absolute and normalizes it. On Windows, all letters are
  converted to lowercase.
  """

  path = os.path.normpath(os.path.abspath(path))
  if os.name == 'nt':
    path = path.lower()
  return path


def get_bootstrap_modules_dir(config):
  """
  Finds the package `ppy_modules/` directory that contains the bootstrap
  modules.
  """

  # Ppy-engine could be installed in development mode, in which case
  # the `ppy_modules/` dir is in the same as the ppy-engine module.
  develop_dir = os.path.normpath(__file__ + '/../../' + PPY_MODULES)
  if os.path.isdir(develop_dir):
    return develop_dir

  # Otherwise, the modules dir is probably the same as the global
  # install directory.
  return os.path.join(config['prefix'], PPY_MODULES)
