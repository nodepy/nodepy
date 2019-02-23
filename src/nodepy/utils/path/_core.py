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

import pathlib2 as pathlib


def lparts(path):
  """
  Yields the components of *path* from left to right.
  """

  return reversed(list(rparts(path)))


def rparts(path):
  """
  Yields the components of *path* from right to left.
  """

  # Yield from the back of the path.
  name = path.name
  if name:
    yield name
  for path in path.parents:
    yield path.name


def upiter(path):
  prev = None
  while prev != path:
    yield path
    prev, path = path, path.parent


def endswith(path, ending):
  if not isinstance(ending, pathlib.Path):
    ending = pathlib.Path(ending)
  for part in rparts(ending):
    if not part:
      continue
    if part != path.name:
      return False
    path = path.parent
  return True


def is_directory_listing_supported(path):
  """
  Returns #True if the specified *path* object support directory listing.
  This is determined by testing it `path.iterdir()` raises a
  #NotImplementedError.
  """

  try:
    path.iterdir()
    return True
  except NotImplementedError:
    return False
