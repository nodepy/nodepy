"""
Iteration utilities.
"""

import collections


class Chain(object):
  """
  Similar to #itertools.chain(), but allows appending iterators on the go.
  """

  def __init__(self, *iterables):
    self.iterables = collections.deque(iter(x) for x in iterables)

  def __iter__(self):
    return self

  def __next__(self):
    while self.iterables:
      try:
        return next(self.iterables[0])
      except StopIteration:
        self.iterables.popleft()
    raise StopIteration

  next = __next__

  def append(self, iterable):
    self.iterables.append(iter(iterable))
    return self

  __lshift__ = append
