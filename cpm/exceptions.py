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


class NotAPackageDirectory(Exception):
  """
  Raised by #core.PackageManifest.parse() when the specified directory is not a
  valid package directory (that is, if it does not contain a `cpm.json` file).
  """

  def __init__(self, directory):
    self.directory = directory

  def __str__(self):
    return 'Not a package directory: "{}"'.format(self.directory)


class InvalidPackageManifest(Exception):
  """
  Raised by #core.PackageManifest.parse() when the package manifest is invalid
  JSON or contains invalid values.
  """

  def __init__(self, filename, cause):
    self.filename = filename
    self.cause = cause

  def __str__(self):
    return 'In file "{}": {}'.format(self.filename, self.cause)


class NoSuchModule(Exception):
  """
  This exception is raised in #core.Package.get_module() if the requested
  module does not exist. If the #module_name attribute is #None, it represents
  the main package module.
  """

  def __init__(self, package, module_name):
    self.package = package
    self.module_name = module_name

  def __str__(self):
    return 'No module "{}" in "{}"'.format(self.module_name,
        self.package.identifier)


class PackageNotFound(Exception):
  """
  This exception is raised if a package is searched but could not be found.
  """

  def __init__(self, package_name, selector):
    self.package_name = package_name
    self.selector = selector or semver.Selector('*')

  def __str__(self):
    return '{}@{}'.format(self.package_name, self.selector)


class PackageMultiplicityNotAllowed(Exception):
  """
  This exception is raised when a package is supposed to be loaded into the
  loaded packages cache but another package with a different version is already
  present.
  """

  def __init__(self, package_name, version, loaded_versions):
    self.package_name = package_name
    self.version = version
    self.loaded_versions = loaded_versions

  def __str__(self):
    version_t = 'version' if len(self.loaded_versions) == 1 else 'versions'
    return 'can not load "{}@{}" load because package multiplicity is '\
        'disabled and the package is already loaded in {} "{}"'.format(
          self.package_name, self.selector, version_t,
          ','.join(map(str, self.loaded_versions)))


class UnknownDependency(Exception):
  """
  This exception is raised when a #core.Module `require()`s another
  #core.Package that is not listed in its dependencies. Note that this
  behaviour can is turned off by default.
  """

  def __init__(self, source_package, package_name):
    self.source_package = source_package
    self.package_name = package_name

  def __str__(self):
    return '"{}" required "{}" which is not a known dependency'.format(
        self.source_package.identifier, self.package_name)


class InstallError(Exception):
  """
  Raised when the installation or uninstallation of a package failed.
  """

  pass
