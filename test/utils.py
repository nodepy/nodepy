
import json
from nodepy.utils import UrlPath
from unittest import TestCase, TestSuite


class TestUrlPath(TestCase):

  def test_urlpath(self):
    path = UrlPath('https://httpbin.org/get?abc=def')
    with path.open() as fp:
      data = json.load(fp)
    self.assertEquals(data['args'], {'abc': 'def'})
