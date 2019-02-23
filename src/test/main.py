"""
Node.py test suite. Not only does the proper execution of this file check if
the Node.py runtime is installed and can be run properly, but also does it
invoke the test cases.
"""

import unittest
import sys

suite = unittest.TestSuite([
  unittest.defaultTestLoader.loadTestsFromModule(require('./utils')),
  unittest.defaultTestLoader.loadTestsFromModule(require('./zippath'))
])

if require.main == module:
  result = unittest.TextTestRunner(verbosity=2).run(suite)
  if result.errors or result.failures:
    sys.exit(1)
  else:
    sys.exit(0)
