"""
Implements the #resolver.StdResolverLoader interface for Python modules.
"""

from nodepy import base, resolver, utils
import sys


class PythonModule(base.Module):

  def _load_code(self):
    with self.filename.open('r') as fp:
      return fp.read()

  def _init_extensions(self, code):
    for ext_module in self.iter_extensions():
      if hasattr(ext_module, 'init_extension'):
        ext_module.init_extension(self.package, self)
      if code is not None and hasattr(ext_module, 'preprocess_python_source'):
        code = ext_module.preprocess_python_source(self, code)
    return code

  def _exec_code(self, code):
    if code:
      code = compile(code, str(self.filename), 'exec', dont_inherit=True)
      exec(code, vars(self.namespace))

  def load(self):
    self.loaded = True
    code = self._load_code()

    # Find the nearest modules directory and enable importing from it.
    # TODO: Could this value be cached on a Package level?
    library_dir = None
    for path in utils.path.upiter(self.directory):
      path = path.joinpath(self.context.pipprefix_directory)
      path = utils.machinery.get_site_packages(path)
      if path.is_dir():
        library_dir = str(path)
        break

    try:
      # NOTE: It's important we do this before extensions are executed.
      # TODO: Maybe add a loader meta_path that can load from any PathLike?
      #       As this, it will only work for filesystem paths.
      if library_dir:
        sys.path.insert(0, library_dir)

      code = self._init_extensions(code)
      self._exec_code(code)
    finally:
      if library_dir:
        try:
          sys.path.remove(library_dir)
        except ValueError:
          pass

  def iter_extensions(self):
    extensions = utils.iter.Chain(self.context.extensions)
    if self.package:
      require = self.package.require
      extensions << (require(ext) for ext in self.package.extensions)
    return extensions


class PythonLoader(resolver.StdResolver.Loader):

  def suggest_files(self, context, path):
    try:
      yield path.with_suffix('.py')
    except ValueError:
      pass
    yield path.joinpath('__init__.py')

  def can_load(self, context, path):
    return path.suffix == '.py'

  def load_module(self, context, package, filename):
    return PythonModule(context, package, filename)


class PackageRootModule(base.Module):

  def load(self):
    self.loaded = True


class PackageRootLoader(resolver.StdResolver.Loader):
  """
  The package root loader is used to load packages that don't have a
  package main file defined and have no `index` file. In that case, an
  empty module is loaded (of type #PackageRootModule).
  """

  def suggest_files(self, context, path):
    return []

  def can_load(self, context, path):
    if path.joinpath(context.package_manifest).is_file():
      return True
    return False

  def load_module(self, context, package, filename):
    return PackageRootModule(context, package, filename)
