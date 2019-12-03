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
Provides the #Registry client class that communicates with a ppy registry
server. The ppy registry provides a REST api for finding packages, downloading
package distributions and additional files, registering new users and
uploading new packages.
"""

import collections
import hammock
import json
import os
import requests
import six
import argschema from './argschema'
import manifest from './manifest'
import semver from './semver'
import refstring from './refstring'
import text from './util/text'
import json from './util/json'


def get_config_registry(config, name):
  reg = 'registry:' + name
  return config.section(reg)


def get_config_registries(config):
  result = []
  default_found = False
  for section in config.sections():
    if section.startswith('registry:'):
      name = section[9:]
      view = get_config_registry(config, name)
      if name == 'default':
        default_found = True
      result.append(view)
  if not default_found:
    try:
      result.insert(0, get_config_registry(config, 'default'))
    except KeyError:
      pass
  return result


def get_package_archive_name(package_name, version):
  """
  Concatenates the *package_name* and *version* and adds the `.tar.gz`
  suffix. All package distribution archives are supposed to be `.tar.gz`
  files.
  """

  argschema.validate('package_name', package_name,
      {'type': [six.text_type, refstring.Package]})
  if isinstance(package_name, six.text_type):
    package_name = refstring.parse_package(package_name)

  return u'{}-{}.tar.gz'.format(six.text_type(package_name).replace('/', '-'), version)


class Error(Exception):
  """
  Raised when an error occurred while communicating with the registry.
  """

  def __init__(self, response, message, body=None):
    self.response = response
    self.message = message
    self.body = body or response.text

  def __str__(self):
    res = '{}\n  Url:  {} -- Status {}'.format(self.message,
        self.response.url, self.response.status_code)
    bdy = text.truncate(str(self.body), 40, 40) if self.body is not None else ''
    if bdy:
      res += '\n  Body: ' + bdy
    return res

  @property
  def status_code(self):
    return self.response.status_code


class PackageNotFound(Exception):
  """
  Raised by #Registry.find_package() if there is no package matching the
  requirements.
  """

  def __init__(self, package_name, version_selector):
    self.package_name = package_name
    self.version_selector = version_selector

  def __str__(self):
    return '{}@{}'.format(self.package_name, self.version_selector)


class RegistryClient(object):
  """
  A client for the ppy package registry REST api. Some actions require
  authorization, such as uploading a new package distribution or additional
  file. The server will reply with an error if an unauthorized request was
  made.

  # Parameters
  base_url (str): The base URL of the package registry.
  username (str): Username for authorized actions.
  password (str): Password for authorized actions.
  """

  @staticmethod
  def get(config, name):
    try:
      regconf = get_config_registry(config, name)
      regurl = regconf['url']
    except KeyError:
      raise ValueError('Registry {!r} is not configured.'.format(name))
    except KeyError:
      raise ValueError('Registry {!r} has no URL configured.'.format(name))
    return RegistryClient(
      name,
      regurl,
      username=regconf.get('username'),
      password=regconf.get('password')
    )

  @staticmethod
  def get_all(config):
    return [RegistryClient.get(config, x.name) for x in get_config_registries(config)]

  def __init__(self, name, base_url, username=None, password=None):
    self.name = name
    self.base_url = base_url
    self.username = username
    self.password = password
    self.api = hammock.Hammock(base_url).api

  def _handle_response(self, response):
    """
    Takes a #requests.Response object and handles the status code and JSON
    response, eventually raising an #Error. Returns the JSON data if the
    response has no error.
    """

    if response.status_code == 500:
      raise Error(response, "Internal Server Error")
    try:
      data = response.json()
    except json.JSONDecodeError as exc:
      raise Error(response, "Invalid JSON returned")

    if 'error' in data:
      if isinstance(data['error'], dict):
        try:
          raise Error(response, data['error']['title'], data['error']['description'])
        except KeyError:
          raise Error(response, "Invalid Error description", data['error'])
      else:
        raise Error(response, str(data['error']))

    return data

  def download(self, package_name, version, filename=None):
    """
    Download the package archive for the specified *package_name* and *version*.
    If *filename* is not specified, the package-archive name is used which is
    generated with #get_package_archive_name(). Note that the file must
    previously be uploaded with `upm upload`.

    Returns a #requests.Response object. The status code of the returned
    response must be checked!
    """

    argschema.validate('package_name', package_name, {'type': six.text_type})
    argschema.validate('version', version, {'type': semver.Version})
    argschema.validate('filename', filename, {'type': [six.text_type, None]})

    if not filename:
      filename = get_package_archive_name(package_name, version)

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

    argschema.validate('package_name', package_name, {'type': six.text_type})
    argschema.validate('version_selector', version_selector,
        {'type': semver.Selector})

    response = self.api.find(package_name, version_selector).GET()
    try:
      data = self._handle_response(response)
    except Error as exc:
      if exc.message == 'Package not found':
        raise PackageNotFound(package_name, version_selector)
      raise

    try:
      # TODO: Pass config props to parse_dict()
      return manifest.parse_dict(data, [], None, None, copy=False)
    except manifest.InvalidPackageManifest as exc:
      raise Error(response, 'Invalid package manifest ({})'.format(exc), data)

  def upload(self, package_name, version, filename, force=False):
    """
    Upload a file for the specified package version. Note that a file that is
    not the package distribution can only be uploaded when the package
    distribution has already been uploaded. If *force* is #True, the file will
    be uploaded and overwritten if it already exists in the registry.
    """

    argschema.validate('package_name', package_name, {'type': six.text_type})
    argschema.validate('version', version, {'type': semver.Version})
    argschema.validate('filename', filename, {'type': six.text_type})
    argschema.validate('force', force, {'type': bool})

    with open(filename, 'rb') as fp:
      files = {os.path.basename(filename): fp}
      params = {'force': 'true' if force else 'false'}
      response = self.api.upload(package_name, version).POST(
          files=files, params=params, auth=(self.username, self.password))

    data = self._handle_response(response)
    return data.get('message')

  def register(self, username, password, email):
    """
    Register a new user on the registry.
    """

    data = {'username': username, 'password': password, 'email': email}
    response = self.api.register().POST(data=data)
    data = self._handle_response(response)
    return data.get('message')

  def terms(self):
    """
    Downloads the Terms of Use from the registry.
    """

    return self._handle_response(self.api.terms.GET())['terms']
