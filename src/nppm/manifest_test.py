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

from nose.tools import *
import manifest from './manifest'

example_manifest = {
  "name": "example-manifest",
  "version": "0.0.1",
  "dependencies": {
    "nodepy-nosetests": "~0.0.5",
    "werkzeug-reloader-patch": "--pure git+https://github.com/nodepy/werkzeug-reloader-patch.git"
  },
  "cfg(dev).dependencies": {
    "spdx-licenses": "--internal git+https://github.com/nodepy/spdx-licenses.git"
  },
  "cfg(prod or nodepy > 2.0.0)": {
    "dependencies": {
      "production-tracker": "--optional vendor/production-tracker"
    }
  }
}

sorted_fields = lambda x: sorted(x, key=lambda x: (x[0] or '', x[1] if len(x) == 3 else ''))


def test_iter_fields():
  result = sorted_fields(manifest.iter_fields(example_manifest))
  assert_equals(result, [(None, 'dependencies', {'nodepy-nosetests': '~0.0.5', 'werkzeug-reloader-patch': '--pure git+https://github.com/nodepy/werkzeug-reloader-patch.git'}), (None, 'name', 'example-manifest'), (None, 'version', '0.0.1'), ('cfg(dev).', 'dependencies', {'spdx-licenses': '--internal git+https://github.com/nodepy/spdx-licenses.git'}), ('cfg(prod or nodepy > 2.0.0)', 'dependencies', {'production-tracker': '--optional vendor/production-tracker'})])

  result = sorted_fields(manifest.iter_fields(example_manifest, 'dependencies'))
  assert_equals(result, [(None, {'nodepy-nosetests': '~0.0.5', 'werkzeug-reloader-patch': '--pure git+https://github.com/nodepy/werkzeug-reloader-patch.git'}), ('cfg(dev).', {'spdx-licenses': '--internal git+https://github.com/nodepy/spdx-licenses.git'}), ('cfg(prod or nodepy > 2.0.0)', {'production-tracker': '--optional vendor/production-tracker'})])


def test_eval_fields():
  result = manifest.eval_fields(example_manifest, {'dev': True})
  assert_equals(result['dependencies'], {'nodepy-nosetests': '~0.0.5', 'werkzeug-reloader-patch': '--pure git+https://github.com/nodepy/werkzeug-reloader-patch.git', 'spdx-licenses': '--internal git+https://github.com/nodepy/spdx-licenses.git'})

  result = manifest.eval_fields(example_manifest, {'dev': False})['dependencies']
  assert_equals(result, {'nodepy-nosetests': '~0.0.5', 'werkzeug-reloader-patch': '--pure git+https://github.com/nodepy/werkzeug-reloader-patch.git'})

  result = manifest.eval_fields(example_manifest, {'prod': True})['dependencies']
  assert_equals(result, {'nodepy-nosetests': '~0.0.5', 'werkzeug-reloader-patch': '--pure git+https://github.com/nodepy/werkzeug-reloader-patch.git', 'production-tracker': '--optional vendor/production-tracker'})
