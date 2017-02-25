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
"""
This module should not be required but only be executed from the installation
process of `@ppym/engine`. It will install the bootstrapped dependencies that
are delivered with the PPY distribution into the global install directory.
"""

if not require.is_main:
  raise RuntimeError('should not be require()d')

import os, sys
ppym = require('@ppym/ppym')

# Packages in their correct installation order.
deps = [
  '@ppym/argschema',
  '@ppym/semver',
  '@ppym/refstring',
  '@ppym/manifest',
  '@ppym/ppym']

cmd = ['install', '-g'] + sys.argv[1:]
cmd.extend(os.path.join(_dirname, 'ppy_modules', dep) for dep in deps)
ppym.cli(cmd)
