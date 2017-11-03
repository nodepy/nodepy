"""
Base classes and interfaces.
"""

from nodepy import context as _context, utils
from nodepy.utils import pathlib
import types
import weakref


class Extension(object):
  """
  This class only documents the interface that is used by the standard Node.py
  runtime and does not need to be subclassed in order to implement an
  extension. An object that provides any of the methods is sufficient (such
  as the root namespace of a module).
  """

  def init_extensions(self, package, module):
    """
    Called when the extension is loaded for a package or module (only when the
    extension is explicitly declared as an extension in the respective entity).
    """

    pass

  def preprocess_python_source(self, module, source):
    """
    Preprocess the source code of a Python module before it is executed. Must
    return the new source code string.
    """

    return source


class Request(object):

  def __init__(self, context, directory, string, additional_search_path=()):
    assert isinstance(context, _context.Context)
    assert isinstance(directory, pathlib.Path)
    assert isinstance(string, str)
    self.context = context
    self.directory = directory
    self.string = string
    self.additional_search_path = additional_search_path

  def __repr__(self):
    return '<Request "{}" from "{}">'.format(self.string, self.directory)

  def is_relative(self):
    return self.string in ('.', '..') or self.string.startswith('./') or \
      self.string.startswith('../')

  def is_absolute(self):
    return os.path.isabs(self.string)

  def is_module(self):
    return not self.is_relative() and not self.is_absolute()

  @property
  def related_paths(self):
    if not hasattr(self, '_related_paths'):
      self._related_paths = []
      for path in utils.path.upiter(self.directory):
        path = path.joinpath(self.context.modules_directory)
        if path.is_dir():
          self._related_paths.append(path)
    return self._related_paths


class Module(object):

  def __init__(self, context, package, filename, directory=None):
    assert isinstance(context, _context.Context) or context is None
    assert isinstance(package, Package) or package is None
    assert isinstance(filename, pathlib.Path)
    assert isinstance(directory, pathlib.Path) or directory is None
    self.context = context
    self.package = package
    self.filename = filename
    self.directory = directory or filename.parent
    self.namespace = None
    self.exports = NotImplemented
    self.loaded = False
    self.exception = None
    self.require = _context.Require(self.context, self.directory)

  def __repr__(self):
    return '<{} {!r} at "{}">'.format(type(self).__name__, self.name, self.filename)

  @property
  def name(self):
    """
    Returns the name of the module. If #Module.package is available, the name
    will be retrieved by creating a relative path from #Module.filename to the
    #Package.directory. If that failes, the #Module.filename's `stem` is
    returned.
    """

    if self.package:
      try:
        rel = self.filename.with_suffix('').relative_to(self.package.directory)
      except ValueError:
        pass
      else:
        parts = filter(bool, utils.path.lparts(rel))
        return self.package.name + '/' + '/'.join(parts)

    return self.filename.stem

  def init(self):
    """
    Called to initialize the #Module.namespace and reset #Module.exports
    and should be used from #Module.load() before the actual module content
    is loaded.
    """

    self.loaded = False
    self.exports = NotImplemented
    self.exception = None
    self.namespace = types.ModuleType(self.name)
    self.namespace.__file__ = str(self.filename)
    self.namespace.module = self
    self.namespace.require = self.require

  def load(self):
    """
    Implemented by subclass. Loads the contents of the module.

    Use #Context.load_module() instead of calling this method directly for
    the standard behaviour and integrity checks (also calls #init()).
    """

    raise NotImplementedError


class Package(object):
  """
  A package is a container for #Module#s and usually represents a physical
  directory on the filesystem that contains a metadata file.

  # Parameters

  directory (pathlib.Path):
    The directory that is this package.

  payload (dict):
    A dictionary that represents the Package metadata in the standard package
    metadata format as defined by the `nodepy.json` specification. The
    following keys are used by the Node.py runtime:

    * `name`
    * `main` (defaults to `"index"`)
    * `extensions` (defaults to an empty list)
    * `resolve_root` (defaults to #None)
  """

  def __init__(self, context, directory, payload):
    assert isinstance(directory, pathlib.Path)

    if 'name' not in payload:
      msg = 'invalid package payload for "{}": no "name" field'
      raise ValueError(msg.format(directory))

    self.context = context
    self.directory = directory
    self.payload = payload
    self.require = _context.Require(context, directory)

  def __repr__(self):
    return '<Package {!r} at "{}">'.format(self.name, self.directory)

  @property
  def name(self):
    return self.payload['name']

  @property
  def extensions(self):
    return self.payload.get('extensions', [])

  @property
  def resolve_root(self):
    return self.payload.get('resolve_root', '')

  @property
  def main(self):
    return self.payload.get('main', 'index')

  @property
  def is_main_defined(self):
    return bool(self.payload.get('main'))


class Resolver(object):
  """
  Interface for objects that can resolve requests for modules.
  """

  def resolve_module(self, request):
    raise NotImplementedError


class ResolveError(Exception):

  def __init__(self, request, search_paths):
    self.request = request
    self.search_paths = search_paths

  def __str__(self):
    lines = [str(self.request.string)]
    if self.search_paths:
      lines.append('  searched in:')
      for path in self.search_paths:
        lines.append('    - {}'.format(path))
    return '\n'.join(lines)
