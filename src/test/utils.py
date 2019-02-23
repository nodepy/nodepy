
from nodepy.utils.path import UrlPath
import json
import socket
import unittest

REMOTE_SERVER = "www.google.com"

def is_connected():
  if hasattr(is_connected, '_result'):
    return is_connected._result
  try:
    host = socket.gethostbyname(REMOTE_SERVER)
    s = socket.create_connection((host, 80), 2)
    is_connected._result = True
  except:
    is_connected._result = False
  return is_connected._result


class TestUrlPath(unittest.TestCase):

  @unittest.skipIf(not is_connected(), "no internet connection")
  def test_urlpath(self):
    path = UrlPath('https://httpbin.org/get?abc=def')
    with path.open() as fp:
      data = json.load(fp)
    self.assertEquals(data['args'], {'abc': 'def'})
