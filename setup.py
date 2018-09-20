
import setuptools
import sys

nodepy_reqs = [
  'localimport>=1.5.2',
  'pathlib2>=2.3.0',
  'six>=1.11.0',
  'nr.cliparser>=0.1.0'
]

nppm_reqs = [
  'appdirs>=1.4.2',
  'distlib>=0.2.4',
  'hammock>=0.2.4',
  'requests>=2.13.0',
  'nr.fs>=1.0.3',
  'nr.parse>=1.0.0'
]

def readme():
  with open('README.md') as fp:
    return fp.read()

setuptools.setup(
  name = 'nodepy-runtime',
  version = '2.1.5',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  url = 'https://github.com/nodepy/nodepy',
  license = 'MIT',
  description = 'Python with a Node.js-like module system.',
  long_description = readme(),
  long_description_content_type = 'text/markdown',
  packages = setuptools.find_packages(),
  install_requires = nodepy_reqs,
  extras_requires = {
    'pm': nppm_reqs,
  },
  entry_points = dict(
    console_scripts = [
      'nodepy{}=nodepy.main:main'.format(v)
        for v in ('', sys.version[0], sys.version[:3])
    ]
  )
)
