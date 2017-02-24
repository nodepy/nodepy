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
import os
import requests

from upython.utils import semver
from upython.core.finder import PackageNotFound

PackageInfo = collections.namedtuple('PackageInfo', 'name version description')


class Registry:
  """
  Wrapper for the REST API of a package registry.
  """

  def __init__(self, base_url, username=None, password=None):
    self.api = hammock.Hammock(base_url).api
    self.username = username
    self.password = password

  def _handle_response(self, response):
    try:
      data = response.json()
    except json.JSONDecodeError as exc:
      if response.status_code == 500:
        raise RegistryError(response.url, 'Internal server error: {}'.format(response.text))
      elif response.status_code == 200:
        raise RegistryError(response.url, 'Invalid JSON response: {}'.format(exc))
      else:
        raise RegistryError(response.url, response.text)
    if data.get('error') or response.status_code == 500:
      message = data.get('error')
      if message and response.status_code == 500:
        message = 'Internal server error: ' + str(message)
      raise RegistryError(response.url, message)
    return data

  def download(self, package_name, version, filename=None):
    """
    Download the package archive for the specified *package_name* and *version*.
    If *filename* is not specified, the package-archive name is used which is
    generated with #make_package_archive_name(). Note that the file must
    previously be uploaded with `upm upload`.

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
    data = self._handle_response(response)
    if response.status_code == 404:
      raise PackageNotFound(package_name, version_selector)
    if data.get('status') != 'ok' or 'manifest' not in data:
      raise RegistryError(response.url, response)
    data = data['manifest']
    return PackageInfo(data['name'], semver.Version(data['version']),
        data.get('description'))

  def upload(self, package_name, version, filename, force=False):
    """
    Upload a file for the specified package version. Note that a file that is
    not the package distribution can only be uploaded when the package
    distribution has already been uploaded. If *force* is #True, the file will
    be uploaded and overwritten if it already exists in the registry.
    """

    assert isinstance(version, semver.Version)
    with open(filename, 'rb') as fp:
      files = {os.path.basename(filename): fp}
      params = {'force': 'true' if force else 'false'}
      response = self.api.upload(package_name, version).POST(
          files=files, params=params, auth=(self.username, self.password))
      data = self._handle_response(response)
      if data.get('status') != 'ok':
        raise RegistryError(response.url, response)

  def register(self, username, password, email):
    """
    Register a new user on the registry.
    """

    response = self.api.register().POST(data={
        'username': username, 'password': password, 'email': email})
    data = self._handle_response(response)
    if data.get('status') != 'ok':
      raise RegistryError(response.url, response)
    return data.get('message')


class RegistryError(Exception):

  def __init__(self, url, message):
    self.url = url
    self.message = message

  def __str__(self):
    return self.message


def make_package_archive_name(package_name, version):
  return '{}-{}.tar.gz'.format(package_name, version)
