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

from nose.tools import *
import {Package, Ref, parse, parse_package} from './refstring'
import {Version, Selector} from './semver'


def test_parse():
  assert_equals(parse('foobar'), Ref(Package(None, 'foobar'), None, None, None))
  assert_equals(parse('@spekklez/foobar'), Ref(Package('spekklez', 'foobar'), None, None, None))
  assert_equals(parse('@spekklez/foobar@1.6.4'), Ref(Package('spekklez', 'foobar'), Selector(Version('1.6.4')), None, None))
  assert_equals(parse('@spekklez/foobar@>=1.6.4'), Ref(Package('spekklez', 'foobar'), Selector('>=1.6.4'), None, None))
  assert_equals(parse('spam@~1.0.0'), Ref(Package(None, 'spam'), Selector('~1.0.0'), None, None))
  assert_equals(parse('spam@~1.0.0/main'), Ref(Package(None, 'spam'), Selector('~1.0.0'), 'main', None))
  assert_equals(parse('spam@~1.0.0/main:run'), Ref(Package(None, 'spam'), Selector('~1.0.0'), 'main', 'run'))
  assert_equals(parse('spam@~1.0.0:run'), Ref(Package(None, 'spam'), Selector('~1.0.0'), None, 'run'))
  with assert_raises(ValueError):
    parse('.')
  with assert_raises(ValueError):
    parse('..')
  with assert_raises(ValueError):
    parse('/')
  with assert_raises(ValueError):
    parse('@/')
  with assert_raises(ValueError):
    parse('@')


def test_parse_package():
  with assert_raises(ValueError):
    parse_package('.')
  with assert_raises(ValueError):
    parse_package('..')
  with assert_raises(ValueError):
    parse_package('/')
  with assert_raises(ValueError):
    parse_package('@/')
  with assert_raises(ValueError):
    parse_package('@')
