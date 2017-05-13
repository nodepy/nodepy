<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# Node.py

[![Build Status](https://travis-ci.org/nodepy/nodepy.svg?branch=master)](https://travis-ci.org/nodepy/nodepy)
[![GitHub version](https://badge.fury.io/gh/nodepy%2Fnodepy.svg)](https://badge.fury.io/gh/nodepy%2Fnodepy)
[![PyPI version](https://badge.fury.io/py/node.py.svg)](https://badge.fury.io/py/node.py)

**nodepy** is a CPython platform heavily inspired by [Node.js] for building
reproducible and easily distributable applications. While it provides its own
package manager **nodepy-pm** (similar to  [npm]), re-using existing standard
Python modules from [PyPI] is highly encouraged.

## Motivation

Python's `import` mechanism is very limited and hardly customizable, which can
lead to problems in pluggable environments such as plugin infrastructures. When
multiple components provide their own version of a Python module, it can lead
to clashes in `sys.modules` and have one component potentially import a module
it did not expect.

Node.js `require()` solves this very elegantly, as it is always first resolved
based on the location of the file that uses it. Just like Node.js' has its
`node_modules/` directory, Node.py resolved requirements in the nearest
`nodepy_modules/` directory.

Of course, this doesn't play well together with Python's `import`s, thus if
multiple Node.py modules require the same Python package of the same version,
it can still lead to clashes. However, the Context in which Node.py executes
modules a completely isolated environment that restores the original state of
`sys.modules` after it is executed using [localimport].

This does indeed solve the above mentioned problem of possible Python module
clashes among pluggable components, only the integrity of dependencies inside
a component need to be complete.

To see Node.py integrated in a pluggable environment, check out [c4ddev] which
can produce a standalone version of Node.py using [standalone-builder]. This
standalone version of Node.py is loaded once for a component and provides a
fully isolated environment for Cinema 4D Python plugins. Additionally,
**nodepy-pm** provides third-party package installation which has not been
so easily possible for Cinema 4D plugins before.

  [c4ddev]: https://github.com/NiklasRosenstein/c4ddev
  [Changelog]: docs/source/changelog.md
  [Documentation]: https://nodepy.github.io/nodepy
  [localimport]: https://github.com/NiklasRosenstein/localimport
  [Node.js]: https://nodejs.org/
  [npm]: https://www.npmjs.com/
  [Pip]: https://pypi.python.org/pypi/pip
  [ppym.org]: https://ppym.org
  [PyPI]: https://pypi.python.org/pypi
  [standalone-builder]: https://github.com/nodepy/standalone-builder

## Features

- Manage project dependencies in a `package.json` file
- Package manager with capabilities to install Node.py and Python modules
- `require()` makes tracking the origin of a dependency more clear and
  enables an arbitrary project structure
- Enables a new syntax to unpack components from a required module similar
  to Python's `from ... import ...`

## Example

```
$ nodepy-pm init
Package Name? myapp
Package Version [1.0.0]?
Description?
Author (Name <Email>)?
License? MIT
$ nodepy-pm install --save py/flask @nodepy/werkzeug-reloader-patch
[ ... ]
$ ls
app.py config.py index.py nodepy_modules/
$ cat index.py
```

```python
import flask
require('@nodepy/werkzeug-reloader-patch').install()
app = require('./app')
{ host, port, debug } = require('./config')
version = require('./package.json')['version']

if require.main == module:
  app.run(host=host, port=port, debug=debug)
```

```
$ nodepy .
```


## Requirements

- Python 2.7.x, 3.3+
- Pip 8.0.0+
- Pygments (optional, for colored exception tracebacks)

## Installation

    pip install node.py

## Additional Links

- [Documentation]
- [Changelog]
