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

import flask
import functools
import json
import os

from nnp.utils import semver
from nnp.core.manifest import PackageManifest, NotAPackageDirectory, InvalidPackageManifest
from .app import app
from .config import config


def response(data, code=200):
  return flask.Response(json.dumps(data), code, mimetype='test/json')


def expect_package_info(version_type=semver.Version):
  def decorator(func):
    @functools.wraps(func)
    def wrapper(package, version, *args, **kwargs):
      try:
        version = version_type(version)
      except ValueError as exc:
        flask.abort(404)
      return func(package, version, *args, **kwargs)
    return wrapper
  return decorator



@app.route('/api/find/<package>/<version>')
@expect_package_info(semver.Selector)
def find(package, version):
  directory = os.path.join(config['nnpmd:prefix'], package)
  print(directory)
  if not os.path.isdir(directory):
    return response({'status': 'not-found'}, 404)

  choices = []
  for have_version in os.listdir(directory):
    try:
      have_version = semver.Version(have_version)
    except ValueError as exc:
      app.logger.warn('invalid version directory found at "{}"'.format(
          os.path.join(directory, have_version)))
      continue
    if version(have_version):
      choices.append(have_version)

  if not choices:
    return response({'status': 'not-found'})

  choice = version.best_of(choices)
  directory = os.path.join(directory, str(choice))
  try:
    manifest = PackageManifest.parse(directory)
  except NotAPackageDirectory:
    app.logger.warn('missing package.json in "{}"'.format(directory))
    return response({'status': 'not-found'})
  except InvalidPackageManifest as exc:
    app.logger.warn('invalid package.json in "{}": {}'.format(directory, exc))
    return response({'status': 'not-found'})
  if manifest.name != package:
    app.logger.warn('"{}" lists unexpected package name "{}"'.format(
        manifest.filename, manifest.name))
    return response({'status': 'not-found'})
  if manifest.version != choice:
    app.logger.warn('"{}" lists unexpected version "{}"'.format(
        manifest.filename, manifest.version))
    return response({'status': 'not-found'})

  with open(manifest.filename) as fp:
    data = json.load(fp)
  data = {'status': 'ok', 'manifest': data}
  return response(data)


@app.route('/api/download/<package>/<version>/<filename>')
@expect_package_info()
def download(package, version, filename):
  """
  Note: Serving these files should usually be replaced by NGinx or Apache.
  """

  directory = os.path.join(config['nnpmd:prefix'], package, str(version))
  directory = os.path.normpath(os.path.abspath(directory))
  return flask.send_from_directory(directory, filename)


@app.route('/api/upload/<package>/<version>', methods=['POST'])
@expect_package_info()
def upload(package, version):
  flask.abort(500)
