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

__all__ = ['Registry', 'PackageNotFound']

import collections
import hammock
import json
import requests
from nnp.utils import semver
from nnp.core.finder import PackageNotFound

PackageInfo = collections.namedtuple('PackageInfo', 'name version description')


class Registry:
  """
  Wrapper for the REST API of a package registry.
  """

  def __init__(self, base_url):
    self.api = hammock.Hammock(base_url).api

  def download(self, package_name, version, filename=None):
    """
    Download the package archive for the specified *package_name* and *version*.
    If *filename* is not specified, the package-archive name is used which is
    generated with #make_package_archive_name(). Note that the file must
    previously be uploaded with `nnpm uploaded`.

    Returns a #requests.Response object.
    """

    assert isinstance(version, semver.Version)
    if not filename:
      filename = make_package_archive_name(package_name, version)
    url = self.api.download(package_name, version, filename)
    response = url.GET()
    response.raise_for_status()
    return response

  def find_package(self, package_name, version_selector):
    """
    Finds the best matching package for the specified *package_name* and
    *version_selector*. If the registry does not provide the package, raises
    a #PackageNotFound exception, otherwise it returns #PackageInfo.
    """

    assert isinstance(version_selector, semver.Selector)
    response = self.api.find(package_name, version_selector).GET()
    try:
      data = response.json()
    except json.JSONDecodeError:
      response.raise_for_status()
      raise RuntimeError('invalid json returned from registry, but OK status')
    if data.get('status') == 'not-found':
      raise PackageNotFound(package_name, version_selector)
    elif data.get('status') == 'error':
      raise RuntimeError(data.get('message'))
    elif data.get('status') == 'ok':
      data = data['manifest']
      return PackageInfo(data['name'], semver.Version(data['version']), data.get('description'))
    else:
      raise RuntimeError('invalid json response')


def make_package_archive_name(package_name, version):
  return '{}-{}.tar.gz'.format(package_name, version)
