
from setuptools import setup, find_packages
import os
import sys

is_dist = any('dist' in x for x in sys.argv[1:])


def readme():
  if os.path.isfile('README.md') and is_dist:
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
  name = 'nodepy-runtime',
  version = '2.0.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = 'A Node.js-like runtime for Python.',
  long_description = readme(),
  url = 'https://github.com/nodepy',
  packages = find_packages(),
  install_requires = ['localimport>=1.5.2', 'pathlib2>=2.3.0', 'six>=1.11.0'],
  entry_points = {
    'console_scripts': [
      'nodepy{}=nodepy.main:main'.format(v)
      for v in ('', sys.version[0], sys.version[:3])
    ]
  }
)
