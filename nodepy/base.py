"""
Base classes and interfaces.
"""

from nodepy import context as _context
from nodepy.utils import pathlib, pathutils
import types
import weakref


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
        rel = self.filename.relative_to(self.package.directory)
      except ValueError:
        pass
      finally:
        return self.package.name + '/' + '/'.join(pathutils.parts(rel))

    return self.filename.stem

  def init(self):
    """
    Called to initialize the #Module.namespace and reset #Module.exports
    and should be used from #Module.load() before the actual module content
    is loaded.
    """

    self.loaded = False
    self.exports = NotImplemented
    self.namespace = types.ModuleType(self.name)
    self.namespace.__file__ = str(self.filename)
    self.namespace.module = self
    self.namespace.require = self.require

  def load(self):
    """
    Implemented by subclass. Load the contents of the module. Remember to
    call #Module.init() from the implementation of this method before the
    module is actually loaded. Must set #Module.loaded to #True.
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
    metadata format as defined by the `.nodepy/package.toml` specification.
    The following keys are used by the Node.py runtime:

    * `package.name`
    * `package.extensions` \*
    * `package.resolve_root` \*
  """

  def __init__(self, directory, payload):
    assert isinstance(directory, pathlib.Path)
    self.directory = directory
    self.require = context.Require(directory)
    self.payload = payload

  def __repr__(self):
    return '<Package {!r} at "{}">'.format(self.name, self.directory)

  @property
  def name(self):
    return self.payload['package']['name']

  @property
  def extensions(self):
    return self.payload['package'].get('extensions', [])

  @property
  def resolve_root(self):
    return self.payload['package'].get('resolve_root', '')


class Resolver(object):
  """
  Interface for objects that can resolve requests for modules.
  """

  def resolve_module(self, request):
    raise NotImplementedError


class Loader(object):
  """
  Interface for the standard #FsResolver that is used to extend the loading
  process of modules from the filesystem.
  """

  def suggest_files(self, path):
    raise NotImplementedError

  def load_modules(self, request, filename):
    raise NotImplementedError


class ResolveError(Exception):

  def __init__(self, request):
    self.request = request

  def __str__(self):
    return str(self.request.string)

