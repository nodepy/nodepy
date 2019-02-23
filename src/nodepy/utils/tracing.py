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

"""
This module provides functionality to inspect the active frames of a running
Python application, which is especially useful when debugging deadlocks.

Inspired by the ActiveState receipe:

  http://code.activestate.com/recipes/577334-how-to-debug-deadlocked-multi-threaded-programs/
"""

import codecs
import io
import os
import sys
import time
import threading
import traceback

try:
  import pygments, pygments.lexers, pygments.formatters
except ImportError:
  pygments = None

try:
  from BaseHTTPServer import HTTPServer
  from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
  from http.server import HTTPServer, SimpleHTTPRequestHandler

stackframes = sys._current_frames
main_thread = next(x for x in threading.enumerate() if isinstance(x, threading._MainThread))


def format_stack(stack):
  lines = []
  for filename, lineno, name, line in traceback.extract_stack(stack):
    lines.append('File: "%s", line %d, in %s' % (filename, lineno, name))
    if line:
      lines.append("  %s" % (line.strip()))
  return '\n'.join(lines)


def format_html(fp, exclude=()):
  frames = stackframes()
  fp.write('<!DOCTYPE html>\n')
  fp.write('<html><head><title>{} Traces</title></head><body>\n'.format(len(frames)))
  for thread_id, stack in sorted(frames.items(), key=lambda x: x[0]):
    name = 'Thread {}'.format(thread_id)
    if thread_id == threading.get_ident():
      name += ' (tracing thread)'
    elif thread_id == main_thread.ident:
      name += ' (main)'
    fp.write('<h3>{}</h3>\n'.format(name))
    tbstr = format_stack(stack)
    if pygments:
      formatter = pygments.formatters.HtmlFormatter(full=False, noclasses=True)
      lexer = pygments.lexers.PythonLexer()
      tbstr = pygments.highlight(tbstr, lexer, formatter)
    fp.write(tbstr)
    fp.write('\n')
  fp.write('</body>\n')


class BaseThread(threading.Thread):

  def __init__(self, *args, **kwargs):
    super(BaseThread, self).__init__(*args, **kwargs)
    self._stop_requested = False
    self._lock = threading.Lock()

  def stop(self, wait=True):
    with self._lock:
      self._stop_requested = True
    if wait:
      self.join()

  def stop_requested(self):
    with self._lock:
      return self._stop_requested

  def start(self, *args, **kwargs):
    with self._lock:
      self._stop_requested = False
    return super(BaseThread, self).start(*args, **kwargs)


class HttpServerTracer(BaseThread):

  class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
      self.send_response(200)
      self.send_header('Content-type', 'text/html')
      self.end_headers()
      fp = codecs.getwriter('utf8')(self.wfile)
      format_html(fp, exclude=(threading.get_ident(),))
    def log_message(self, format, *args):
      pass

  def __init__(self, host=None, port=None):
    super(HttpServerTracer, self).__init__()
    self.host = host or 'localhost'
    self.port = port or 8081
    self.httpd = HTTPServer((self.host, self.port), self.RequestHandler)

  def stop(self, wait=True):
    self.httpd.shutdown()
    super(HttpServerTracer, self).stop(wait)

  def run(self):
    print('Started HttpServerTracer on http://{}:{}'.format(self.host, self.port))
    self.httpd.serve_forever()


class HtmlFileTracer(BaseThread):

  def __init__(self, fname, interval=None):
    super(HtmlFileTracer, self).__init__()
    self._fname = fname or 'trace.html'
    self._interval = interval or 5.0

  def run(self):
    print('Started HtmlFileTracer to "{}" at an interval of {}s'
      .format(self._fname, self._interval))
    while not self.stop_requested():
      with open(self._fname, 'w') as fp:
        format_html(fp)
      time.sleep(self._interval)
