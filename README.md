<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# nodepy

[![Build Status](https://travis-ci.org/nodepy/nodepy.svg?branch=master)](https://travis-ci.org/nodepy/nodepy)
[![GitHub version](https://badge.fury.io/gh/nodepy%2Fnodepy.svg)](https://badge.fury.io/gh/nodepy%2Fnodepy)
[![PyPI version](https://badge.fury.io/py/node.py.svg)](https://badge.fury.io/py/node.py)

**nodepy** is a CPython platform heavily inspired by [Node.js] for building
reproducible and easily distributable applications. While it provides its own
package infrastructure similar to [npm], re-using existing standard Python
modules from [PyPI] is highly encouraged by the package manager, **nodepy-pm**,
which is automatically installed with nodepy.

A usage example to whet your appetite:

    $ nodepy-pm install --save py/flask werkzeug-reloader-patch
    $ cat index.py
    import flask
    require('werkzeug-reloader-patch').install()
    app = require('./app')
    app.run()
    $ nodepy .

  [Node.js]: https://nodejs.org/
  [npm]: https://www.npmjs.com/
  [PyPI]: https://pypi.python.org/pypi
  [Pip]: https://pypi.python.org/pypi/pip
  [ppym.org]: https://ppym.org
  [Documentation]: https://nodepy.github.io/nodepy
  [Changelog]: docs/source/changelog.md

## Requirements

- Python 2.7.x, 3.3+
- Pip 8.0.0+

## Installation

    pip install node.py

## Additional Links

- [Documentation]
- [Changelog]
