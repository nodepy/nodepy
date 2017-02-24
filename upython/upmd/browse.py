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

from flask import abort, request, render_template
from .app import app
from .models import *


@app.route('/')
def index():
  return render_template('index.html', nav='index')


@app.route('/browse')
def browse():
  return render_template('browse.html', nav='browse')


@app.route('/package/<package>')
def package(package):
  package = Package.objects(name=package).first()
  if not package:
    abort(404)
  return render_template('package.html', nav='browse', package=package, version=package.latest)


@app.route('/package/<package>/<version>')
def package_version(package, version):
  package = Package.objects(name=package).first()
  if not package:
    abort(404)
  version = PackageVersion.objects(package=package, version=version).first()
  if not version:
    abort(404)
  return render_template('package.html', nav='browse', package=package, version=version)


@app.route('/user/<user>')
def user(user):
  user = User.objects(name=user).first()
  if not user:
    abort(404)
  return render_template('user.html', nav='browse', user=user)


@app.route('/validate-email/<token>')
def validate_email(token):
  user = User.objects(validation_token=token).first()
  if not user or user.validated:
    abort(404)
  user.validated = True
  user.validation_token = None
  user.save()
  return render_template('validated.html', user=user)
