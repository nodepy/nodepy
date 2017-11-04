"""
Node.py test suite. Not only does the proper execution of this file check if
the Node.py runtime is installed and can be run properly, but also does it
invoke the test cases.
"""

import unittest
import test_utils from './utils.py'

suite = unittest.defaultTestLoader.loadTestsFromModule(test_utils)

if require.main == module:
  unittest.TextTestRunner(verbosity=2).run(suite)
