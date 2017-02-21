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

__all__ = ['Finder', 'StandardFinder', 'PackageNotFound']

import os
from .manifest import *
from .package import *


class Finder:
  """
  Interface for package finders.
  """

  def find_package(self, package_name, version_selector):
    """
    Find a #PackageManifest for a given *package_name* and *version_selector*.
    If multiple packages matching the criteria are found, the best matching
    (aka. newest) version number should be returned.

    # Raises
    PackageNotFound:
    """

    raise PackageNotFound(package_name, version_selector)

  def get_manifest_cache(self, directory):
    """
    Returns the #PackageManifest for *directory* if it is already cached in
    this #Finder, otherwise #None.
    """

    return None


class StandardFinder(Finder):
  """
  A class to find packages in a directory. Packages must be sub-directories of
  the actual search-directory that contain a `package.json` file. Below is an
  example of which files can be detected given that the search directory is
  `upython_packages/`.

      package.json (not detected)
      upython_packages/package.json  (not detected)
      upython_packages/demo-app/package.json (detected)

  # Members

  directory (str): The directory to search in.
  cache (dict of (str, PackageManifest)): A dictionary that caches the manifest
    information read in for every package directory.
  """

  def __init__(self, directory):
    self.directory = directory
    self.cache = {}
    self.update()

  def load_package(self, directory):
    """
    Manually add a package in *directory* to the #cache. This will allow the
    package to be returned by #find_package() if the criteria matches. If the
    package at *directory* is already in the cache, it will not be re-parsed.

    # Raise
    NotAPackageDirectory
    InvalidPackageManifest

    # Return
    PackageManifest
    """

    directory = os.path.normpath(os.path.abspath(directory))
    try:
      manifest = self.cache[directory]
    except KeyError:
      self.cache[directory] = manifest = PackageManifest.parse(directory)
    return manifest

  def update(self, error_strategy='report'):
    """
    This method is automatically called when the #StandardFinder is constructed.
    If the #directory changed, this method should be called again. Note that
    packages that have been found and cached once will not be re-parsed unless
    #flush() is called.

    If *error_strategy* is `'report'`, invalid package manifests that are
    encountered will be reported to stderr. Another possible value is
    `'collect'` in which case a list of the encountered errors is returned
    instead.
    """

    if error_strategy not in ('report', 'collect'):
      raise ValueError('invalid error_strategy: {!r}'.format(error_strategy))
    report = (error_strategy == 'report')
    errors = None if report else []

    if not os.path.isdir(self.directory):
      return errors

    for subdir in os.listdir(self.directory):
      subdir = os.path.join(self.directory, subdir)
      if not os.path.isdir(subdir):
        continue

      try:
        self.load_package(subdir)
      except NotAPackageDirectory as exc:
        pass  # We don't mind if it is not a package directory
      except InvalidPackageManifest as exc:
        if report:
          print('warning:', exc)
        else:
          errors.append(exc)

    return errors

  def find_package(self, package_name, selector):
    " Overwrites #Finder.find_package(). "

    best_match = None
    for manifest in self.cache.values():
      if package_name and manifest.name != package_name:
        continue
      if selector and not selector(manifest.version):
        continue
      if best_match is None or best_match.version < manifest.version:
        best_match = manifest

    if not best_match:
      raise PackageNotFound(package_name, selector)

    return best_match

  def get_manifest_cache(self, directory):
    " Overwrites #Finder.get_manifest_cache(). "
    directory = os.path.normpath(os.path.abspath(directory))
    return self.cache.get(directory)


class PackageNotFound(Exception):

  def __init__(self, package_name, selector):
    self.package_name = package_name
    self.selector = selector

  def __str__(self):
    return '"{}@{}" could not be found'.format(self.package_name, self.selector)
