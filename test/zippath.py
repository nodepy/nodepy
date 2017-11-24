
import io
import nodepy
import os
import unittest
import zipfile


class TestZipPath(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    # Create zipfile in memory that contains some Python source files,
    # allowing us to test the require() process from ZIP files.
    fp = io.BytesIO()
    zipf = zipfile.ZipFile(fp, 'w')
    zipf.writestr('ziptest.py', b"import './deep/module'\n")
    zipf.writestr('deep/module.py', b"import '../notsodeep.py'\n")
    zipf.writestr('notsodeep.py', b"\n")
    zipf.close()
    fp.seek(0)

    cls.zipf = zipfile.ZipFile(fp, 'r')

  def setUp(self):
    self.ctx = nodepy.context.Context()
    self.ctx.resolver.paths.append(nodepy.utils.path.ZipPath(self.zipf, '/'))

  def testRequireFromZip(self):
    self.ctx.require('ziptest')
