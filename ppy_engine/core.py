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

PPY_MODULES = 'ppy_modules'
PACKAGE_JSON = 'package.json'


class ResolveError(Exception):
  """
  Raised when a module name could not be resolved.
  """


class Session(object):
  """
  A session represents a complete and isolated ppy environment.
  """

  def __init__(self, config=None):
    self.config = config = config or Config()
    self.path = []
    self.main_module = None
    self.module_cache = {}
    self.manifest_cache = {}
    self.current_modules = collections.deque()
    self.preserve_symlinks = config.get('preserve_symlinks') == 'true'

    prefix = config.get('prefix')
    if prefix:
      self.path.append(os.path.join(prefix, PPY_MODULES))
    self.path.extend(filter(bool, config.get('path', '').split(os.pathsep)))
    self.path.extend(filter(bool, os.environ.get('PPY_PATH', '').split(os.pathsep)))

    # For now, standard Python modules are only support from the the local
    # `ppy_modules/.pymodules` directory. In the future, we may add loading
    # Python modules with a separate `localimport` for *every*
    # `ppy_modules/.pymodules` directory.
    self.localimport = localimport.localimport([PPY_MODULES + '/.pymodules'], '.')

  def __enter__(self):
    self.localimport.__enter__()
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

  def get_manifest(self, filename):
    """
    Parses a #PackageManifest from *filename* and returns it. The manifest
    is cached by the absolute and normalized *filename*.
    """

    filename = os.path.normpath(os.path.abspath(filename))
    if filename in self.manifest_cache:
      return self.manifest_cache[filename]
    manifest = PackageManifest.parse_file(filename)
    self.manifest_cache[filename] = manifest
    return manifest

  def get_module(self, filename):
    """
    Returns a #Module from the specified *filename*. If the module is not
    already cached, it will be created. Note that the module is not necessarily
    loaded. You can do that with #Module.load().
    """

    filename = os.path.normpath(os.path.abspath(filename))
    if filename in self.module_cache:
      return self.module_cache[filename]
    module = Module(filename, self)
    self.module_cache[filename] = module
    return module

  def resolve(self, request, current_dir=None, is_main=False):
    """
    Uses #resolve_module_filename() and raises #ResolveError if the *request*
    could not be resolved. Returns a #Module object. If *is_main* is #True,
    the #Session.main_module will be set. Note that if #Session.main_module
    is already set, a #RuntimeError will be raised if *is_main* is #True.
    """

    if is_main and self.main_module:
      raise RuntimeError('already have a main module')
    current_dir = current_dir or os.getcwd()
    filename = self.resolve_module_filename(request, current_dir, is_main)
    if not filename:
      raise RuntimeError(request, current_dir)
    module = self.get_module(filename)
    if is_main:
      self.main_module = module
    return module

  def resolve_module_filename(self, request, current_dir, is_main):
    """
    Resolves the filename for a Python module from the specified *request*
    name. This may be a relative name like `./path/to/module` in which case
    it is evaluated solely in *current_dir*. Otherwise, if the requested module
    is in standard format (eg. `module-name/core`), the module name is resolved
    in the ppy search path.

    If no file can be found, #None is returned.
    """

    def try_file_(filename):
      return try_file(filename, self.preserve_symlinks and not is_main)

    if os.path.isabs(request):
      main = 'index.py'
      if os.path.isdir(request):
        mffile = os.path.join(request, PACKAGE_JSON)
        if os.path.isfile(mffile):
          # TODO: Only log invalid manifests..?
          main = self.get_manifest(mffile).main
      return try_file_(request) or try_file_(request + '.py') \
          or try_file_(os.path.join(request, main))

    current_dir = current_dir or os.getcwd()
    if request.startswith('./') or request.startswith('..1/'):
      filename = os.path.normpath(os.path.join(current_dir, request))
      return self.resolve_module_filename(filename, current_dir, is_main)

    for path in itertools.chain(self.iter_module_paths(current_dir), self.path):
      filename = os.path.normpath(os.path.abspath(os.path.join(path, request)))
      filename = self.resolve_module_filename(filename, current_dir, is_main)
      if filename:
        return filename

    return None

  def iter_module_paths(self, from_dir):
    """
    Yield all possible `ppy_modules/` paths that can be matched starting from
    *from_dir*. Note that the method can yield directories that don't exist.
    """

    from_dir = os.path.normpath(os.path.abspath(from_dir))
    while from_dir:
      dirname, base = os.path.split(from_dir)
      if base != PPY_MODULES:
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


class Module(object):
  """
  Represents a ppy Python module.
  """

  def __init__(self, filename, session):
    self.filename = filename
    self.directory = os.path.dirname(filename)
    self.namespace = types.ModuleType(filename)
    self.session = session
    self.loaded = False

    # Initialize the module's namespace.
    self.namespace.__filename = filename
    self.namespace.__dirname = os.path.dirname(filename)
    self.namespace.require = Require(self)

  def __repr__(self):
    return '<Module {!r}>'.format(self.filename)

  def load(self):
    if self.loaded:
      raise RuntimeError('module already loaded')
    self.loaded = True
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

  def __init__(self, module):
    self.module = module
    self.session = module.session

  def __repr__(self):
    return '<Require of {!r}>'.format(self.module)

  def __call__(self, name):
    filename = self.session.resolve_module_filename(name, self.module.__dirname)
    if not filename:
      raise ResolveError(name, self.module.__dirname)
    module = self.session.get_module(filename)
    if not module.loaded:
      module.load()
    return module


def try_file(filename, preserve_symlinks, is_main=False):
  """
  Returns *filename* if it exists. If *is_main* is #False and
  `--preserve-symlinks`, symlinks will be kept intact.
  """

  if os.path.isfile(filename):
    if not preserve_symlinks and not is_main and os.path.islink(filename):
      os.path.relpath(filename)
    return filename
  return None
