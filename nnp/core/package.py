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

__all__ = ['Module', 'Package', 'NoSuchModule']

import os
import types


class Module:
  """
  This class represents an actual Python file that can be executed directly
  via **nnp** or be `require()`d by another module. A module may not be part
  of a #Package if it is executed directly (depending on whether the package
  can be resolved from the module's location).
  """

  def __init__(self, package, filename):
    self.package = package
    self.filename = filename
    self.executed = False
    self.namespace = types.ModuleType(self.identifier)
    self.namespace.__name__ = self.name
    self.namespace.__file__ = filename

  def __str__(self):
    exec_info = '' if self.executed else ' (not executed)'
    return '<Module "{}" from "{}"{}>'.format(
        self.identifier, self.filename, exec_info)

  @property
  def name(self):
    if not self.package:
      return '__main__'
    name = self.filename[:-3] if self.filename.endswith('.py') else self.filename
    return os.path.relpath(name, self.package.directory)

  @property
  def identifier(self):
    if not self.package:
      return '/__main__'
    return '{}/{}'.format(self.package.identifier, self.name)


class Package:
  """
  This class represents a package and provides access to its submodules.
  """

  def __init__(self, manifest, module_class=Module):
    self.manifest = manifest
    self.module_class = module_class
    self.modules = {}

  def __str__(self):
    return '<Package "{}" from "{}">'.format(self.identifier, self.directory)

  @property
  def name(self):
    return self.manifest.name

  @property
  def version(self):
    return self.manifest.version

  @property
  def identifier(self):
    return self.manifest.identifier

  @property
  def directory(self):
    return self.manifest.directory

  def load_module_from_filename(self, filename):
    """
    Loads a module from a filename. If the filename ends with `.py`, the
    actual correct reference to the module is returned. If it is any other
    filename, a new #Module is returned that is not actually cached in
    #Package.modules.
    """

    if not os.path.isabs(filename):
      rel = os.path.relpath(filename, self.directory)
    else:
      rel = filename
    if rel == os.curdir or rel.startswith(os.pardir):
      raise ValueError('"{}" not part of this package'.format(filename))

    if rel.endswith('.py'):
      return self.load_module(rel[:-3])
    return self.module_class(self, filename)

  def load_module(self, name=None):
    """
    Returns a #Module instance from the specified module *name*. If #None is
    passed, the package's main module will be loaded.

    # Raises
    NoSuchModule
    """

    if name is None:
      name = self.manifest.main
    if name in self.modules:
      return self.modules[name]

    filename = os.path.join(self.manifest.directory, name + '.py')
    filename = os.path.normpath(os.path.abspath(filename))
    if not os.path.isfile(filename):
      raise NoSuchModule(self, name)

    module = self.module_class(self, filename)
    self.modules[name] = module
    return module


class NoSuchModule(Exception):
  """
  This exception is raised in #Package.load_module() if the requested module
  does not exist.
  """

  def __init__(self, package, module_name):
    self.package = package
    self.module_name = module_name

  def __str__(self):
    return 'No module "{}" in "{}"'.format(
        self.module_name, self.package.identifier)
