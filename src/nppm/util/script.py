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

"""
Helper function to create script files for pure Python code, ppy modules or
shell commands. Uses the Python #distlib package.
"""

import errno
import os
import re
import textwrap
import six
import sys
try:
  from distlib.scripts import ScriptMaker as _ScriptMaker
except ImportError as exc:
  from pip._vendor.distlib.scripts import ScriptMaker as _ScriptMaker

try:
  from shlex import quote
except ImportError:
  from pipes import quote


def winquote(s):
  s = s.replace('"', '\\"')
  if re.search('\s', s) or any(c in s for c in '<>'):
    s = '"' + s + '"'
  return s


class ScriptMaker:
  """
  Our own script maker class. It is unlike #distutils.script.ScriptMaker.
  """

  def __init__(self, config, directory, location):
    assert location in ('root', 'global', 'local')
    self.config = config
    self.directory = directory
    self.location = location
    self.path = []
    self.pythonpath = []

  def _init_code(self):
    code = textwrap.dedent('''
      # Initialize environment variables (from ScriptMaker).
      import os, sys
      curdir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
      try: sys.path.remove(curdir)
      except ValueError: pass
    ''')
    if self.path:
      path = [os.path.abspath(x) for x in self.path]
      code += (
        'os.environ["PATH"] = os.pathsep.join({path!r}) + os.pathsep + os.environ.get("PATH", "")\n'
        .format(path=path)
      )
    code += 'sys.path.extend({pythonpath!r})\n'.format(
      pythonpath=[os.path.abspath(x) for x in self.pythonpath]
    )
    # Remember: We don't set PYTHONPATH due to nodepy/nodepy#62
    return code

  def _get_maker(self):
    return _ScriptMaker(None, self.directory)

  def _use_distlib(self):
    try:
      use_distlib = self.config['install.use_distlib']
    except KeyError:
      # On Windows, we'll use the distlib ScriptMaker if the Python executable
      # is not on a path with whitespace in it. If it has whitespace, we must
      # fallback on your own mechanism that works WITH spaces.
      if os.name == 'nt' and ' ' in sys.executable:
        use_distlib = False
      else:
        use_distlib = True
    else:
      use_distlib = str(use_distlib).strip().lower()
      use_distlib = (use_distlib in ('yes', 'on', 'true', '1'))
    return use_distlib

  def get_files_for_script_name(self, script_name):
    """
    Returns the filenames that would be created by one of the `make_...()`
    functions.
    """

    outname = os.path.join(self.directory, script_name)

    if self._use_distlib():
      maker = self._get_maker()
      # Reproduces _ScriptMaker._write_script() a little bit.
      use_launcher = maker.add_launchers and maker._is_nt
      if use_launcher:
        n, e = os.path.splitext(script_name)
        if e.startswith('.py'):
          outname = n
        outname = '{}.exe'.format(outname)
      else:
        if maker._is_nt and not outname.endswith('.py'):
          outname += '.py'
      return [outname]
    else:
      result = [outname]
      if os.name == 'nt':
        result += [outname + '.py', outname + '.cmd']
      return result

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

    if self._use_distlib():
      return self.__make_python_distlib(script_name, code)
    else:
      # The ScriptMaker can make .exe files, but they can sometimes be
      # problematic, thus we default to manually creating the script files
      # on Windows.
      return self.__make_python_custom(script_name, code)

  def __make_python_distlib(self, script_name, code):
    if os.name == 'nt' and (not script_name.endswith('.py') \
        or not script_name.endswith('.pyw')):
      # ScriptMaker._write_script() will split the extension from the script
      # name, thus if there is an extension, we should add another suffix so
      # the extension doesn't get lost.
      script_name += '.py'

    maker = self._get_maker()
    maker.clobber = True
    maker.variants = set(('',))
    maker.set_mode = True
    maker.script_template = self._init_code() + code
    return maker.make(script_name + '=isthisreallynecessary')

  def __make_python_custom(self, script_name, code):
    code = self._init_code() + code
    exec_permissions = int('755', 8)

    try:
      os.makedirs(self.directory)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise

    unix_fn = os.path.join(self.directory, script_name)
    if os.name == 'nt':
      python_fn = unix_fn + '.py'
      # The shebang isn't really used on Windows, but we include it in case
      # you look into the file and wonder what it needs to be executed with.
      # PyLauncher can work with it, but only if it's properly quoted. Quotes
      # are usually NOT supported in the shebang.
      python_shebang = quote(sys.executable)
    else:
      python_fn = unix_fn
      python_shebang = sys.executable

    with open(python_fn, 'w') as fp:
      fp.write('#!' + sys.executable + '\n')
      fp.write(code)
    os.chmod(python_fn, exec_permissions)

    files = [python_fn]

    if os.name == 'nt':
      assert unix_fn != python_fn
      files.append(unix_fn)
      with open(unix_fn, 'w') as fp:
        fp.write('#!bash\n')
        fp.write('{} "$(dirname ${{BASH_SOURCE[0]}})/{}" "$@"\n'.format(quote(sys.executable), os.path.basename(python_fn)))
      os.chmod(unix_fn, exec_permissions)

      batch_fn = os.path.join(self.directory, script_name + '.cmd')
      files.append(batch_fn)
      with open(batch_fn, 'w') as fp:
        fp.write('@{} "%~dp0{}" %*\n'.format(winquote(sys.executable), os.path.basename(python_fn)))
      os.chmod(batch_fn, exec_permissions)

    return files

  def make_command(self, script_name, args):
    """
    Uses #make_python() to create a Python script that uses the #subprocess
    module to run the command specified with *args*.
    """

    code = 'import sys, subprocess, os\n'\
           'os.environ["PYTHONPATH"] = os.pathsep.join({pythonpath!r}) + os.pathsep + os.environ.get("PYTHONPATH", "")\n'\
           'sys.exit(subprocess.call({!r} + sys.argv[1:]))\n'.format(args, pythonpath=self.pythonpath)
    return self.make_python(script_name, code)

  def make_nodepy(self, script_name, filename):
    """
    Uses #make_pyton() to create a script that invokes the current Python and
    Node.py runtime to run the Node.py module specified by *filename*.
    """

    args = ['--keep-arg0']
    args.append(filename)

    code = (
      'import sys, nodepy.main, nodepy.runtime\n'
      'nodepy.runtime.script = {{"location": {location!r}, "original_path": sys.path[:], "args": sys.argv[:]}}\n'
      'sys.argv = [sys.argv[0]] + {args!r} + sys.argv[1:]\n'
      'sys.exit(nodepy.main.main())\n'
      .format(args=args, location=self.location)
    )
    return self.make_python(script_name, code)

  def make_wrapper(self, script_name, target_program):
    """
    Creates a Python wrapper script that will invoke *target_program*. Before
    the program is invoked, the environment variables PATH and PYTHONPATH will
    be prefixed with the paths from *path* and *pythonpath*.
    """

    if isinstance(target_program, str):
      if not os.path.isabs(target_program):
        raise ValueError('target_program must be an absolute path')
      target_program = [target_program]

    return self.make_command(script_name, target_program)
