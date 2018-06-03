
import setuptools
import sys


def readme():
  with open('README.md') as fp:
    return fp.read()


def requirements():
  with open('requirements.txt') as fp:
    return fp.readlines()


setuptools.setup(
  name = 'nodepy-runtime',
  version = '2.0.3',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  url = 'https://github.com/nodepy/nodepy',
  license = 'MIT',
  description = 'Python with a Node.js-like module system.',
  long_description = readme(),
  long_description_content_type = 'text/markdown',
  packages = setuptools.find_packages(),
  install_requires = requirements(),
  entry_points = dict(
    console_scripts = [
      'nodepy{}=nodepy.main:main'.format(v)
        for v in ('', sys.version[0], sys.version[:3])
    ]
  )
)
