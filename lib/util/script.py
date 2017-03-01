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
from distlib.scripts import ScriptMaker

argschema = require('../argschema')


def make_python_script(script_name, directory, code):
  """
  Uses #distlib.scripts.ScriptMaker to create a Python script that is invoked
  with this current interpreter. The script runs *code* and will be created
  in the specified *directory*.

  # Parameters
  script_name (str): The name of the script to create.
  directory (str): The directory to create the script in.
  code (str): The python code to run.

  # Returns
  A list of filenames created. Depending on the platform, more than one file
  might be created to support multiple use cases (eg. and `.exe` but also a
  bash-script on Windows).
  """

  maker = ScriptMaker(None, directory)
  maker.clobber = True
  maker.variants = set(('',))
  maker.set_mode = True
  maker.script_template = code
  return maker.make(script_name + '=isthisreallynecessary')


def make_command_script(script_name, directory, args):
  """
  Uses #make_python_script() to create a Python script that uses the
  #subprocess module to run the command specified with *args*.
  """

  argschema.validate('args', args, {'type': [list, tuple],
      'items': {'type': str}})
  code = 'import subprocess\n'\
         'import sys\n'\
         'sys.exit(subprocess.call({!r}))\n'.format(args)
  return make_python_script(script_name, directory, code)


def make_nodepy_script(script_name, directory, filename, reference_dir=None):
  """
  Uses #make_python_script() to create a script that invokes the current
  python and ppy runtime to run the ppy module specified by *filename*.
  If a *reference_dir* is specified, that directory will be used as a
  the base directory to start searching for `ppy_modules/` directories
  instead of the current working directory.
  """

  argschema.validate('filename', filename, {'type': str})
  argschema.validate('reference_dir', reference_dir, {'type': [str, None]})

  args = []
  if reference_dir:
    # Find modules in the reference directory.
    args.append('--current-dir')
    args.append(reference_dir)
  args.append(filename)

  code = 'import sys\n'\
         'import nodepy\n'\
         'sys.argv = [sys.argv[0]] + {args!r} + sys.argv[1:]\n'\
         'sys.exit(nodepy.cli())\n'.format(args=args)

  return make_python_script(script_name, directory, code)
