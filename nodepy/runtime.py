
import os
import sys

#: This value is set automatically before the Node.py entry point is invoked
#: from scripts that are installed via the Node.py package manager. It will be
#: a dictionary with the following keys:
#:
#: * location: Either `system`, `global` or `local`
#: * original_path: The original value of `sys.path` before it was augmented
#:   by the Node.py entry point.
script = None

#: A list of command-line arguments to spawn a new Node.py child-process.
#: This is usually the Python interpreter and the path to the Node.py Python
#: module.
exec_args = [sys.executable, os.path.dirname(__file__)]

#: The name of the Python implementation that we're running, eg. cpython,
#: pypy, jython, ironpython, etc.
implementation = None
if hasattr(sys, 'implementation'):
  implementation = sys.implementation.name.lower()
else:
  implementation = sys.subversion[0].lower()
