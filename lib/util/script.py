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
Helper function to create script files for pure Python code, ppy modules or
shell commands. Uses the Python #distlib package.
"""

import os
import six
from distlib.scripts import ScriptMaker as _ScriptMaker

argschema = require('../argschema')


class ScriptMaker:
  """
  Our own script maker class. It is unlike #distutils.script.ScriptMaker.
  """

  def __init__(self, directory):
    self.directory = directory
    self.path = []
    self.pythonpath = []

  def _init_code(self):
    if not self.path and not self.pythonpath:
      return ''
    code = '# Initialize environment variables (from ScriptMaker).\nimport os,sys\n'
    if self.path:
      path = [os.path.abspath(x) for x in self.path]
      code += 'os.environ["PATH"] = os.pathsep.join({path!r}) + '\
              'os.pathsep + os.environ.get("PATH", "")\n'.format(path=path)
    if self.pythonpath:
      path = [os.path.abspath(x) for x in self.pythonpath]
      code += '_add_pythonpath = {pythonpath!r}\n'\
              'sys.path.extend(_add_pythonpath); del _add_pythonpath\n'.format(pythonpath=path)
    return code + '\n'

  def make_python(self, script_name, code):
    """
    Uses #distlib.scripts.ScriptMaker to create a Python script that is invoked
    with this current interpreter. The script runs *code* and will be created
    in the *directory* specified in the constructor of this #ScriptMaker.

    # Parameters
    script_name (str): The name of the script to create.
    code (str): The python code to run.

    # Returns
    A list of filenames created. Depending on the platform, more than one file
    might be created to support multiple use cases (eg. and `.exe` but also a
    bash-script on Windows).
    """

    if os.name == 'nt' and (not script_name.endswith('.py') \
        or not script_name.endswith('.pyw')):
      # ScriptMaker._write_script() will split the extension from the script
      # name, thus if there is an extension, we should add another suffix so
      # the extension doesn't get lost.
      script_name += '.py'

    maker = _ScriptMaker(None, self.directory)
    maker.clobber = True
    maker.variants = set(('',))
    maker.set_mode = True
    maker.script_template = self._init_code() + code
    return maker.make(script_name + '=isthisreallynecessary')

  def make_command(self, script_name, args):
    """
    Uses #make_python() to create a Python script that uses the #subprocess
    module to run the command specified with *args*.
    """

    code = 'import sys, subprocess\n'\
           'sys.exit(subprocess.call({!r}))\n'.format(args)
    return self.make_python(script_name, code)

  def make_nodepy(self, script_name, filename, reference_dir=None):
    """
    Uses #make_pyton() to create a script that invokes the current Python and
    Node.py runtime to run the Node.py module specified by *filename*. If a
    *reference_dir* is specified, that directory will be used as a the base
    directory to start searching for `nodepy_modules/` directories instead of
    the current working directory.
    """

    args = ['--keep-arg0']
    if reference_dir:
      # Find modules in the reference directory.
      args.append('--current-dir')
      args.append(reference_dir)
    args.append(filename)

    code = 'import sys, nodepy;\n'\
           'sys.argv = [sys.argv[0]] + {args!r} + sys.argv[1:]\n'\
           'sys.exit(nodepy.main())\n'.format(args=args)
    return self.make_python(script_name, code)

  def make_wrapper(self, script_name, target_program):
    """
    Creates a Python wrapper script that will invoke *target_program*. Before
    the program is invoked, the environment variables PATH and PYTHONPATH will
    be prefixed with the paths from *path* and *pythonpath*.
    """

    if not os.path.isabs(target_program):
      raise ValueError('target_program must be an absolute path')

    code = 'import subprocess, sys\n'\
           'sys.exit(subprocess.call([{program!r}] + sys.argv[1:]))\n'\
             .format(program=target_program)
    return self.make_python(script_name, code)
