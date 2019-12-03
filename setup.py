
import io
import re
import setuptools
import sys

with io.open('src/nodepy/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['appdirs >=1.4.2,<2.0.0', 'distlib >=0.2.4,<0.3.0', 'hammock >=0.2.4,<0.3.0', 'localimport >=1.5.2,<2.0.0', 'nr.fs >=1.5.0,<2.0.0', 'nr.parsing.core >=0.1.0,<0.2.0', 'pathlib2 >=2.3.0,<3.0.0', 'requests >=2.13.0,<3.0.0', 'six >=1.11.0,<2.0.0']

import os, fnmatch
def _collect_data_files(data_files, target, path, include, exclude):
  for root, dirs, files in os.walk(path):
    parent_dir = os.path.normpath(os.path.join(target, os.path.relpath(root, path)))
    install_files = []
    for filename in files:
      filename = os.path.join(root, filename)
      if include and not any(fnmatch.fnmatch(filename, x) for x in include):
        continue
      if exclude and any(fnmatch.fnmatch(filename, x) for x in exclude):
        continue
      install_files.append(filename)
    data_files.setdefault(parent_dir, []).extend(install_files)

data_files = {}
_collect_data_files(data_files, 'data/nodepy-runtime/stdlib/nppm', 'src/nppm/', ['*.py'], [])
data_files = list(data_files.items())

setuptools.setup(
  name = 'nodepy-runtime',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Python with a Node.js-like module system.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/nodepy/nodepy',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'nppm', 'nppm.*']),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  tests_require = [],
  python_requires = None, # TODO: None,
  data_files = data_files,
  entry_points = {
    'console_scripts': [
      'nodepy = nodepy.main:main',
      'nodepy{0} = nodepy.main:main'.format(sys.version[0]),
      'nodepy{0} = nodepy.main:main'.format(sys.version[:3]),
    ]
  }
)
