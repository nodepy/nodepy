
import io
import re
import setuptools
import sys

with io.open('nodepy/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['localimport >=1.5.2,<2.0.0', 'pathlib2 >=2.3.0,<3.0.0', 'six >=1.11.0,<2.0.0']

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
  packages = setuptools.find_packages('.'),
  package_dir = {'': '.'},
  include_package_data = False,
  install_requires = requirements,
  tests_require = [],
  python_requires = None, # TODO: None,
  entry_points = {
    'console_scripts': [
      'nodepy = nodepy.main:main',
      'nodepy{0} = nodepy.main:main'.format(sys.version[0]),
      'nodepy{0} = nodepy.main:main'.format(sys.version[:3]),
    ],
  }
)
