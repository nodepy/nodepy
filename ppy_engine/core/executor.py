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

__all__ = ['Executor', 'ExecuteError']

import collections
import sys
from .manifest import *
from .package import *
from .finder import *


class Executor:
  """
  Executor for #Module objects.
  """

  def __init__(self, initializers=()):
    self.initializers = list(initializers)
    self.module_stack = collections.deque()

  @property
  def current_module(self):
    """
    Returns the #Module that is currently being executed by this #Executor.
    """

    if not self.module_stack:
      return None
    return self.module_stack[-1]

  def exec_module(self, module):
    """
    Exeuctes the specified #Module object. Raises #RuntimeError if the module
    was already executed. If an exception occurs during the execution of the
    module, an #ExecuteError is raised.
    """

    if module.executed:
      raise RuntimeError('Module already executed')

    with open(module.filename, 'r') as fp:
      code = fp.read()

    module.executed = True
    self.module_stack.append(module)
    try:
      for func in self.initializers:
        func(module)
      try:
        code = compile(code, module.filename, 'exec')
        exec(code, vars(module.namespace))
      except ExecuteError:
        raise
      except BaseException:
        raise ExecuteError(module, sys.exc_info())
    finally:
      assert self.module_stack.pop() is module


class ExecuteError(Exception):

  def __init__(self, module, exc_info):
    self.module = module
    self.exc_info = exc_info

  def __str__(self):
    return 'Error in "{}": {}'.format(self.module.identifier, self.exc_info[1])
