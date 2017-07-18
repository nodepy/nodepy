<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# Node.py

[![Build Status](https://travis-ci.org/nodepy/nodepy.svg?branch=master)](https://travis-ci.org/nodepy/nodepy)
[![GitHub version](https://badge.fury.io/gh/nodepy%2Fnodepy.svg)](https://badge.fury.io/gh/nodepy%2Fnodepy)
[![PyPI version](https://badge.fury.io/py/node.py.svg)](https://badge.fury.io/py/node.py)

**nodepy** is a CPython platform heavily inspired by [Node.js] for building
reproducible and easily distributable applications. While it provides its own
package manager **nppm** (similar to  [npm]), re-using existing standard
Python modules from [PyPI] is highly encouraged.

__Additional Links__

- [Documentation]
- [Changelog]

## Motivation

Python's Import-mechanism is very limited and hardly customizable, which can
lead to problems in pluggable environments such as plugin infrastructures. When
multiple components provide their own version of a Python module, it can lead
to clashes in `sys.modules` and have one component potentially import the
wrong module. Node.js" `require()` solves this very elegantly, as it is always
first resolved based on the location of the file that uses it. Just like
Node.js' has its `node_modules/` directory, Node.py resolved requirements in
the nearest `nodepy_modules/` directory.

**nppm** is an [npm]-inspired package manager for Node.py packages.

  [c4ddev]: https://github.com/NiklasRosenstein/c4ddev
  [Changelog]: docs/source/changelog.md
  [Documentation]: https://nodepy.github.io/nodepy/
  [localimport]: https://github.com/NiklasRosenstein/localimport
  [Node.js]: https://nodejs.org/
  [npm]: https://www.npmjs.com/
  [Pip]: https://pypi.python.org/pypi/pip
  [PyPI]: https://pypi.python.org/pypi
  [standalone-builder]: https://github.com/nodepy/standalone-builder

## Features

- Manage project dependencies in a `package.json` file
- Package manager with capabilities to install Node.py and Python modules
- `require()` makes tracking the origin of a dependency more clear and
  enables an arbitrary project structure
- Run-time extensions (eg. source code preprocessors)

## Requirements

- Python 2.7.x, 3.3+
- Pip 8.0.0+
- Wheel 0.29.0+ (for correct Pip installations with `--prefix`)
- Pygments (optional, for colorised exception tracebacks)
- Colorama (optional, for colorised output on Windows)

## Installation

    pip install node.py

## Building the Documentation

Install [yassg], the build the documentation.

    $ nppm install -g git+https://github.com/NiklasRosenstein/yassg.git
    $ cd docs
    $ yassg

[yassg]: https://github.com/NiklasRosenstein/yassg
