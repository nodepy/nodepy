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

import sys
import pip.req
from setuptools import setup, find_packages
from setuptools.command.install import install

if sys.version_info[0] != 3:
  raise EnvironmentError('requires Python3')

parse_requirements = lambda fn: [
    str(x.req) for x in pip.req.parse_requirements(
      fn, session=pip.download.PipSession())]


class PostInstallCommand(install):
  """
  Post installation command to install `ppym`.
  """

  def run(self):
    super(PostInstallCommand, self).run()
    import ppy_engine.main
    print('Running ppym/selfinstall.py ...')
    ppy_engine.main.cli(['postinstall.py'])


setup(
  name = 'ppy-engine',
  version = '0.0.3',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = '',
  url = 'https://github.com/ppym/ppy-engine',
  packages = find_packages(),
  install_requires = parse_requirements('requirements.txt'),
  entry_points = {
    'console_scripts': [
      'ppy = ppy_engine.main:cli'
    ]
  },
  cmdclass = {
    'install': PostInstallCommand
  }
)
