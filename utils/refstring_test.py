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

from nose.tools import *
from cpm.utils.refstring import parse, join, Ref
from cpm.utils.semver import Selector


def test_parse():
  assert_equals(parse('foobar'), Ref('foobar', None, None, None))
  assert_equals(parse('foobar@2.3.1'), Ref('foobar', Selector('2.3.1'), None, None))
  assert_equals(parse('foobar@2.3.x'), Ref('foobar', Selector('2.3.x'), None, None))
  assert_equals(parse('foobar@=1.0.0 || ~2.1.5-alpha || ^3.6.9/index'), Ref('foobar', Selector('=1.0.0 || ~2.1.5-alpha || ^3.6.9'), 'index', None))
  assert_equals(parse('foobar@2.3.1/index'), Ref('foobar', Selector('2.3.1'), 'index', None))
  assert_equals(parse('foobar@2.3.1/index:func'), Ref('foobar', Selector('2.3.1'), 'index', 'func'))

