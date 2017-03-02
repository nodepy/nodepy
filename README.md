<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# Node.py

[![Build Status](https://travis-ci.org/nodepy/nodepy.svg?branch=master)](https://travis-ci.org/nodepy/nodepy)
[![GitHub version](https://badge.fury.io/gh/nodepy%2Fnodepy.svg)](https://badge.fury.io/gh/nodepy%2Fnodepy)
[![PyPI version](https://badge.fury.io/py/node.py.svg)](https://badge.fury.io/py/node.py)

Node.py is a loader for Python modules in the Node.js-style. Unlike standard
Python modules, the Node.py `require()` caches modules by their filename and
thus allows modules with the same name be loaded from multiple locations at
the same time.

The goal of this project is to develop a Python environment that can execute
without module collisions (resulting in one component in the process recieving
the wrong module) and a more sophisticated approach to the module finding and
loading process.

Node.py has its own package ecosystem managed by [ppym] and the
[PPYM package registry].

  [ppym]: https://github.com/nodepy/ppym
  [PPYM package registry]: https://github.com/nodepy/ppym-registry

__Requirements__

- Python 2.7+ or Python 3.3+
- Pip 6+

__Installation__

    pip install node.py

__Synopsis__

    node.py            (enter interactive session)
    node.py <request>  (resolve request into a filename and run it as a
                        Python script in Node.py environment)

__Todo__

- Alternative script names for `node.py` and `ppym` depending on the Python
  version it is installed into
- Support many of Node.js's original command-line arguments
- Testcases for Python 2 and 3

## Changelog

### v0.0.10

- extensions are now checked in the order they are registered
- support loading bytecache files with the suffix `.cpython-XY.pyc`
- the `.py` loader now loads the respective bytecache file if appropriate
- `Context.register_binding()` now accepts arbitrary objects, not just
  `BaseModule` instances
- add `require.current` and `Context.current_module` properties
- support for `.nodepy-link` files as created by `ppym install -e`

### v0.0.9

- `setup.py` -- Fix creation of `node.py` script on Windows by hooking
  `distlib.scripts.ScriptMaker` (see issue #11)
- `require.main` property can now be set
- update bundled PPYM to v0.0.7
- `setup.py` now always upgrades to the bundled PPYM installation
