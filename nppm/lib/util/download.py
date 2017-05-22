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

import posixpath
import requests
import sys
import time

from six.moves import urllib


def get_response_filename(response):
  """
  Returns the filename from a #requests.Response object. If the
  `Content-Disposition` header is present, the filename in that header will
  be returned, otherwise the basename of the URL is used.
  """

  disp = response.headers.get('Content-Disposition')
  if disp:
    return parse_content_disposition(disp)['filename']
  return posixpath.basename(urllib.parse.urlsplit(response.url)[2])


def parse_content_disposition(disp):
  """
  Parses the `Content-Disposition` header and returns a dictionary.
  """

  func = lambda x: x.strip().split('=', 1) if '=' in x else (x.strip(), '')
  data = dict(map(func, disp.split(';')))
  if 'filename' in data:
      data['filename'] = data['filename'].strip("\"'")
  return data


class DownloadProgress:
  """
  Progress-printer for the #download_to_fileobj() function.
  """

  def __init__(self, width=50, prefix='', print_num_progress=True, print_performance=True):
    self.width = width
    self.prefix = prefix
    self.spin_offset = 0
    self.print_num_progress = print_num_progress
    self.print_performance = print_performance
    self.last_update = 0
    self.last_bytes_written = 0

  def init(self, content_length, response):
    pass

  def finish(self, content_length, bytes_written):
    sys.stdout.write('\n')

  def update(self, content_length, bytes_written):
    sys.stdout.write('\r\33[K' + self.prefix)
    if content_length:
      count = int(bytes_written / content_length * self.width)
      sys.stdout.write('[' + '=' * count + ' ' * (self.width - count) + ']')
    else:
      sys.stdout.write('[' + '~' * self.spin_offset + '=' +
          '~' * (self.width - self.spin_offset - 1) + ']')
      self.spin_offset = (self.spin_offset + 1) % self.width

    if self.print_num_progress:
      # TODO: Convert bytes to human readable
      sys.stdout.write(' ({}/{})'.format(bytes_written, content_length))

    if self.print_performance:
      delta_time = time.time() - self.last_update
      delta_bytes = bytes_written - self.last_bytes_written
      if delta_time > 0.0:
        # TODO: Convert bytes to human readable
        performance = delta_bytes / delta_time
        sys.stdout.write(' {} Bps'.format(performance))
      self.last_update = time.time()
      self.last_bytes_written = bytes_written


def download_to_fileobj(response, fp, progress=False, chunk_size=50):
  try:
    content_length = int(response.headers.get('Content-Length', 'spam'))
  except ValueError:
    content_length = None

  if progress is True:
    progress = DownloadProgress()

  if progress:
    progress.init(content_length, response)
  bytes_written = 0
  for data in response.iter_content(chunk_size=chunk_size):
    fp.write(data)
    bytes_written += len(data)
    if progress:
      progress.update(content_length, bytes_written)
  if progress:
    progress.finish(content_length, bytes_written)
