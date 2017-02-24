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
from flask_httpauth import HTTPBasicAuth
from ..config import config
from ..core import PackageManifest, NotAPackageDirectory, InvalidPackageManifest
from ..utils import semver
from ..upm.registry import make_package_archive_name
from .app import app
from .models import User, Package, PackageVersion, hash_password

auth = HTTPBasicAuth()


@auth.hash_password
def hash_pw(username, password):
  return hash_password(password)


@auth.get_password
def get_pw(username):
  user = User.objects(name=username).first()
  if user:
    return user.passhash
  return None


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

  directory = os.path.join(config['upmd.prefix'], package)
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

  directory = os.path.join(config['upmd.prefix'], package, str(version))
  directory = os.path.normpath(os.path.abspath(directory))
  return flask.send_from_directory(directory, filename)


@app.route('/api/upload/<package>/<version>', methods=['POST'])
@auth.login_required
@expect_package_info()
@json_catch_error()
@on_return()
def upload(on_return, package, version):
  user = User.objects(name=auth.username()).first()
  assert user
  if not user.validated:
    return response({'error': 'your email address is not verified'}, 403)

  # If the package already exists, make sure the user is authorized.
  has_package = Package.objects(name=package).first()
  owner = has_package.owner if has_package else None
  if owner and owner.name != auth.username():
    return response({'error': 'not authorized to manage package "{}", '
        'it belongs to "{}"'.format(package, owner.name)}, 400)

  force = request.args.get('force', 'false').lower().strip() == 'true'
  if len(request.files) != 1:
    return response({'error': 'zero or more than 1 file(s) uploaded'}, 400)

  filename, storage = next(request.files.items())
  if filename == 'package.json':
    return response({'error': '"package.json" can not be uploaded directly'}, 400)

  directory = os.path.join(config['upmd.prefix'], package, str(version))
  absfile = os.path.join(directory, filename)
  if os.path.isfile(absfile) and not force:
    return response({'error': 'file "{}" already exists'.format(filename)}, 400)

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
    if not manifest.license:
      return response({'error': 'packages on the registry must have a '
          '`license` defined in the manifest'}, 400)
    if not os.path.isdir(directory):
      os.makedirs(directory)
    tar.extract('package.json', directory)
    shutil.copyfile(tmp.name, absfile)
  elif not os.path.isfile(os.path.join(directory, 'package.json')):
    return response({'error': 'package distribution must be uploaded before '
        'any additional files can be accepted'}, 400)
  else:
    manifest = None
    storage.save(absfile)

  # If the package doesn't belong to anyone, we'll add it to the user.
  if not owner:
    user = User.objects(name=auth.username()).first()
    has_package = Package(name=package, owner=user)
    has_package.save()
    print('Added package', package, 'to user', user.name)

  # Create the version if it doesn't exist already.
  if manifest:
    pv = PackageVersion.objects(package=has_package, version=str(manifest.version)).first()
    if not pv:
      pv = PackageVersion(package=has_package, version=str(manifest.version))
      pv.save()
      print('Added version', manifest.version, 'to package', package)

  return response({'status': 'ok'})


@app.route('/api/register', methods=['POST'])
def register():
  username = request.form.get('username')
  password = request.form.get('password')
  email = request.form.get('email')
  if not username or len(username) < 3 or len(username) > 24:
    return response({'error': 'no or invalid username specified'}, 400)
  if not password or len(password) < 6 or len(password) > 64:
    return response({'error': 'no or invalid password specified'}, 400)
  if not email or len(email) < 4 or len(email) > 64:
    return response({'error': 'no or invalid email specified'}, 400)

  user = User.objects(name=username).first()
  if user:
    return response({'error': 'user "{}" already exists'.format(username)}, 400)
  if User.objects(email=email).first():
    return response({'error': 'email "{}" already in use'.format(email)}, 400)
  user = User(name=username, passhash=hash_password(password), email=email,
      validation_token=None, validated=False)
  user.send_validation_mail()
  user.save()

  message = 'User registered successfully. Please verify your e-mail address '\
      'by visiting the link we just sent you.'
  if app.debug:
    message += ' DEBUG: Verify URL: {}'.format(user.get_validation_url())
  return response({'status': 'ok', 'message': message})
