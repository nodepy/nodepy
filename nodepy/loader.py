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
Implements the #resolver.StdResolverLoader interface for Python modules.
"""

from nodepy import base, resolver, utils
import codecs
import sys


class PythonModule(base.Module):

  def _load_code(self):
    # TODO: Properly peek into the file for a coding: <name> instruction.
    with self.filename.open('rb') as fp:
      return codecs.getreader('utf8')(fp).read()

  def _init_extensions(self):
    for ext_module in self.iter_extensions():
      if hasattr(ext_module, 'init_extension'):
        ext_module.init_extension(self.package, self)

  def _preprocess_code(self, code):
    if code:
      for ext_module in self.iter_extensions():
        if hasattr(ext_module, 'preprocess_python_source'):
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
      if library_dir and library_dir not in sys.path:
        sys.path.insert(0, library_dir)

      self._init_extensions()
      code = self._preprocess_code(code)
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
