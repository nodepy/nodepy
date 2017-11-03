"""
Replica of the standard #json module, but defines #JSONDecodeError in
Python 2 as well.
"""

from __future__ import absolute_import
from json import *

try: JSONDecodeError
except NameError: JSONDecodeError = ValueError
