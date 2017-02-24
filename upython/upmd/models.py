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

__all__ = ['User', 'Package', 'PackageVersion']

import flask
import uuid

from datetime import datetime
from hashlib import sha512
from mongoengine import *
from ..config import config
from .email import make_smtp, MIMEText

connect(
  db = config['upmd.mongodb_database'],
  host = config['upmd.mongodb_host'],
  port = int(config['upmd.mongodb_port']),
  username = config.get('upmd.mongodb_user'),
  password = config.get('upmd.mongodb_password')
)


class User(Document):
  name = StringField(required=True, unique=True, min_length=3, max_length=64)
  passhash = StringField(required=True)
  email = StringField(required=True, min_length=4, max_length=54)
  created = DateTimeField(default=datetime.now)
  validation_token = StringField()
  validated = BooleanField()

  def send_validation_mail(self):
    """
    Sends an email with a email verification link. The user must be saved
    after this method is called.
    """

    self.validation_token = str(uuid.uuid4())
    me = config['upmd.email_origin']
    html = flask.render_template('validate-email.html', user=self)
    part = MIMEText(html, 'html')
    part['Subject'] = 'Validate your upmpy.org email'
    part['From'] = me
    part['To'] = self.email
    s = make_smtp()
    s.sendmail(me, [self.email], part.as_string())
    s.quit()

  def get_validation_url(self):
    res = config['upmd.visible_url_scheme'] + '://'
    res += config['upmd.visible_host']
    res += flask.url_for('validate_email', token=self.validation_token)
    return res


class Package(Document):
  name = StringField(required=True, unique=True)
  owner = ReferenceField('User', DENY)
  latest = ReferenceField('PackageVersion', DENY)
  created = DateTimeField(default=datetime.now)


class PackageVersion(Document):
  package = ReferenceField('Package', CASCADE)
  version = StringField(required=True, min_length=1)
  created = DateTimeField(default=datetime.now)
  files = ListField(StringField())


def hash_password(password):
  return sha512(password.encode('utf8')).hexdigest()
