
from setuptools import setup, find_packages
import os
import sys


def readme():
  """
  This helper function uses the `pandoc` command to convert the `README.md`
  into a `README.rst` file, because we need the long_description in ReST
  format. This function will only generate the `README.rst` if any of the
  `setup dist...` commands are used, otherwise it will return an empty string
  or return the content of the already existing `README.rst` file.
  """

  if os.path.isfile('README.md') and any('dist' in x for x in sys.argv[1:]):
    if os.system('pandoc -s README.md -o README.rst') != 0:
      print('-----------------------------------------------------------------')
      print('WARNING: README.rst could not be generated, pandoc command failed')
      print('-----------------------------------------------------------------')
      if sys.stdout.isatty():
        input("Enter to continue... ")
    else:
      print("Generated README.rst with Pandoc")

  if os.path.isfile('README.rst'):
    with open('README.rst') as fp:
      return fp.read()
  return ''


setup(
  name = 'node.py',
  version = '0.1.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = 'A Node.js-like runtime for Python (incl. package manager).',
  long_description = readme(),
  url = 'https://github.com/nodepy',
  packages = find_packages(),
  install_requires = ['localimport>=1.5.2', 'pathlib2>=2.3.0', 'toml>=0.9.3'],
  entry_points = {
    'console_scripts': [
      'nodepy{} = nodepy.main:main'.format(v)
      for v in ('', sys.version[0], sys.version[:3])
    ]
  }
)
