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

Version = require('./semver').Version
Selector = require('./semver').Selector

def test_version():
  assert Version('1').mmp == (1, 0, 0)
  assert Version('7.42').mmp == (7, 42, 0)
  assert Version('3.9.1').mmp == (3, 9, 1)
  assert Version('1.7.42-extension').mmp == (1, 7, 42)
  assert Version('1.7.42-extension').extension == 'extension'
  assert Version('1.7.42-beta-foo67bar+baz-build09').mmpeb == (1, 7, 42, 'beta-foo67bar', 'baz-build09')
  assert Version('1.0') <= Version('1.0.19-alpha')
  assert Version('1.0.19-alpha') >= Version('1.0')
  assert Version('1.0.1') >= Version('1.0')
  assert not Version('1.0.1') < Version('1.0')
  assert not Version('1.32.0') <= Version('1.9.2')
  assert Version(Version('1.0.9-alpha')) == Version('1.0.9-alpha')

@raises(ValueError)
def test_version_invalid1():
  Version('1.0.42.')

def test_version_cmp():
  assert Version('1') == Version('1.0')
  assert Version('1') == Version('1.0.0')
  assert Version('1.1') > Version('1.0.0')
  assert Version('1.0.0') < Version('1.0.1')
  assert Version('1') <= Version('1.0.0')
  assert Version('1.0-alpha') < Version('1')
  assert Version('1.0-alpha') < Version('1.0.0')
  assert Version('1.0.0') > Version('1.0-alpha')

def test_version_satisfies():
  assert not Version('1.2.3').satisfies('=1.0')
  assert not Version('1.2.3').satisfies('=1.0 || >2.5')
  assert Version('1.2.3').satisfies('=1.0 || >2.5 || 0.9 - 1.3.0-rc1')
  assert Version('1.2.3-alpha').satisfies('0.9 - 1.3.0-rc1')

def test_version_attr():
  ver = Version('1.42.9-alpharc1')
  ver.major = 2
  ver.minor -= 2
  ver.patch += 1
  ver.extension = 'gammaray5'
  assert ver == Version('2.40.10-gammaray5')

def test_critera():
  with assert_raises(ValueError) as exc:
    Selector('')

  assert Selector('~ 1.0')(Version('1.0.1'))
  assert Selector('~ 1.0')(Version('1.0.6'))
  assert Selector('~ 1.0')(Version('1.0.19-alpha'))
  assert Selector('~ 1.0')(Version('1.0.1-rc1+build112'))
  assert Selector('1.0 - 1.9.2')(Version('1.0'))
  assert Selector('1.0 - 1.9.2')(Version('1.9.2'))
  assert Selector('1.0 - 1.9.2')(Version('1.8-alpha'))
  assert not Selector('1.0 - 1.9.2')(Version('1.32'))
  assert not Selector('>2.5')(Version('1.2.3'))

  versions = [Version('1.9.3'), Version('1.2.3'), Version('1.2.6'), Version('1.2.7')]
  assert Selector('~1.2.5').best_of(versions, is_sorted=True) == Version('1.2.6')
  assert Selector('~1.2.5').best_of(versions) == Version('1.2.7')

  assert_equals(str(Selector("1.x.9-alpha")), "1.x.9-alpha")
  assert_equals(str(Selector("1.x.9-x")), "1.x.9-x")
  assert_equals(str(Selector("1.x.9-alpha")), "1.x.9-alpha")
  assert_equals(str(Selector("1.x.9-x")), "1.x.9-x")
  assert_equals(str(Selector("1.9.224-x")), '1.9.224-x')
  assert Selector("1.x")(Version('1.9.224'))
  assert Selector("1.x")(Version('1.9.224-alpha'))
  assert Selector("1.9.224-x")(Version('1.9.224-alpha'))
  assert Selector("1.x.x")(Version('1.9.224'))
  assert Selector("1.x.x")(Version('1.3.224'))
  assert Selector("x.6.x")(Version('5.6.2'))
  assert Selector("x.6.x")(Version('1.6.9'))
  assert not Selector("x.6.x")(Version('1.7.9'))

@raises(AssertionError)
def test_critera_invalid1():
  assert Selector('~ 1.0')(Version('1.0.0-rc1'))
