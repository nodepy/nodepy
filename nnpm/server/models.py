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

__all__ = ['client', 'db', 'hash_password', 'Error', 'User']

from datetime import datetime
from hashlib import sha512
from mongoengine import *
from .config import config

connect(
  db = config['nnpmd:mongodb_database'],
  host = config['nnpmd:mongodb_host'],
  port = int(config['nnpmd:mongodb_port']),
  username = config.get('npmd:mongodb_user'),
  password = config.get('npmd:mongodb_password')
)


class Error(Exception):
  pass


class User(Document):
  name = StringField(required=True, min_length=3, max_length=64)
  passhash = StringField(required=True)
  email = StringField(required=True, min_length=4, max_length=54)
  created = DateTimeField(default=datetime.now)
  packages = ListField(StringField(max_length=64))


def hash_password(password):
  return sha512(password.encode('utf8')).hexdigest()
