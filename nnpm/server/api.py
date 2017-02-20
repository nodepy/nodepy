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
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import traceback

from flask import request
from nnp.utils import semver
from nnp.core.manifest import PackageManifest, NotAPackageDirectory, InvalidPackageManifest
from .app import app
from .config import config
from ..registry import make_package_archive_name


def response(data, code=200):
  return flask.Response(json.dumps(data), code, mimetype='test/json')


def expect_package_info(version_type=semver.Version, json=True):
  def decorator(func):
    @functools.wraps(func)
    def wrapper(package, version, *args, **kwargs):
      try:
        version = version_type(version)
      except ValueError as exc:
        if json:
          return response({'error': str(exc)}, 404)
        else:
          flask.abort(404)
      return func(package, version, *args, **kwargs)
    return wrapper
  return decorator


def json_catch_error():
  def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except Exception as exc:
        traceback.print_exc()
        if app.debug:
          return response({'error': str(exc)}, 500)
        else:
          return response({'error': "internal server error"}, 500)
    return wrapper
  return decorator


def on_return():
  def decorator(func):
    handlers = []
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
      return func(handlers, *args, **kwargs)
    return wrapper
  return decorator


@app.route('/api/find/<package>/<version>')
@json_catch_error()
@expect_package_info(semver.Selector)
def find(package, version):
  def not_found(): return response({'status': 'package-not-found'}, 404)

  directory = os.path.join(config['nnpmd:prefix'], package)
  print(directory)
  if not os.path.isdir(directory):
    return not_found()

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
    return not_found()

  choice = version.best_of(choices)
  directory = os.path.join(directory, str(choice))
  try:
    manifest = PackageManifest.parse(directory)
  except NotAPackageDirectory:
    app.logger.warn('missing package.json in "{}"'.format(directory))
    return not_found()
  except InvalidPackageManifest as exc:
    app.logger.warn('invalid package.json in "{}": {}'.format(directory, exc))
    return not_found()
  if manifest.name != package:
    app.logger.warn('"{}" lists unexpected package name "{}"'.format(
        manifest.filename, manifest.name))
    return not_found()
  if manifest.version != choice:
    app.logger.warn('"{}" lists unexpected version "{}"'.format(
        manifest.filename, manifest.version))
    return not_found()

  with open(manifest.filename) as fp:
    data = json.load(fp)
  data = {'status': 'ok', 'manifest': data}
  return response(data)


@app.route('/api/download/<package>/<version>/<filename>')
@expect_package_info(json=False)
def download(package, version, filename):
  """
  Note: Serving these files should usually be replaced by NGinx or Apache.
  """

  directory = os.path.join(config['nnpmd:prefix'], package, str(version))
  directory = os.path.normpath(os.path.abspath(directory))
  return flask.send_from_directory(directory, filename)


@app.route('/api/upload/<package>/<version>', methods=['POST'])
@json_catch_error()
@expect_package_info()
@on_return()
def upload(on_return, package, version):
  force = request.args.get('force', 'false').lower().strip() == 'true'
  if len(request.files) != 1:
    return response({'error': 'zero or more than 1 file(s) uploaded'}, 400)

  filename, storage = next(request.files.items())
  if filename == 'package.json':
    return response({'error': '"package.json" can not be uploaded directory'}, 400)

  directory = os.path.join(config['nnpmd:prefix'], package, str(version))
  absfile = os.path.join(directory, filename)
  if os.path.isfile(absfile) and not force:
    return response({'error': 'file "{}" already exists'.format(filename)})

  if filename == make_package_archive_name(package, version):
    # Save the file to a temporary path because we can only read from the
    # FileStorage once.
    with tempfile.NamedTemporaryFile(suffix='_' + filename, delete=False) as tmp:
      shutil.copyfileobj(storage, tmp)
    on_return.append(tmp.delete)
    try:
      tar = tarfile.open(tmp.name, mode='r')
      on_return.append(tar.close)
      fp = io.TextIOWrapper(tar.extractfile('package.json'))
      manifest = PackageManifest.parse_file(fp, directory)
    except KeyError as exc:
      tar.close()
      return response({'error': str(exc)}, 400)
    except InvalidPackageManifest as exc:
      return response({'error': 'invalid package manifest: {}'.format(exc)}, 400)
    if not os.path.isdir(directory):
      os.makedirs(directory)
    tar.extract('package.json', directory)
    shutil.copyfile(tmp.name, absfile)
  elif not os.path.isfile(os.path.join(directory, 'package.json')):
    return response({'error': 'package distribution must be uploaded before '
        'any additional files can be accepted'}, 400)
  else:
    storage.save(absfile)

  return response({'status': 'ok'})
