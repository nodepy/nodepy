
import io
import setuptools
import sys

aliases = ['nodepy{}'.format(v) for v in ('', sys.version[0], sys.version[:3])]

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nodepy-runtime',
  version = '2.1.5',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  url = 'https://github.com/nodepy/nodepy',
  license = 'MIT',
  description = 'Python with a Node.js-like module system.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = [
    'localimport>=1.5.2',
    'pathlib2>=2.3.0',
    'six>=1.11.0',
  ],
  entry_points = {
    'console_scripts': ['{}=nodepy.main:main'.format(x) for x in aliases]
  }
)
