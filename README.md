<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# Node.py

[![Build Status](https://travis-ci.org/nodepy/nodepy.svg?branch=master)](https://travis-ci.org/nodepy/nodepy)
[![GitHub version](https://badge.fury.io/gh/nodepy%2Fnodepy.svg)](https://badge.fury.io/gh/nodepy%2Fnodepy)
[![PyPI version](https://badge.fury.io/py/node.py.svg)](https://badge.fury.io/py/node.py)

Node.py is a loader for Python modules that offers a `require()` function.
Unlike standard Python modules, Node.py modules are cached by their filename,
thus multiple modules with the same name but from different locations can be
loaded without collisions.

Node.py has its own package ecosystem managed by [PPYM] and the
[PPYM package registry]. Check out the [Documentation].

  [ppym]: https://github.com/nodepy/ppym
  [PPYM package registry]: https://github.com/nodepy/ppym-registry
  [Documentation]: https://nodepy.github.io/nodepy/

__Requirements__

- Python 2.7+ or Python 3.3+
- Pip 8+ for PPYM (uses `--prefix`)

__Installation__

    pip install node.py

## Building the Documentation

The documentation can be found in the `docs/` directory. It is based on MkDocs
and can be built by using the PPYM package manager by first installing the
dependencies and then running the `build` script.

    $ cd docs
    $ ppym install
    $ ppym run build

## Changelog

### v0.0.11

- add `Require.__call__(current_dir=None, is_main=False, cache=True)` arguments\
- add `Require.exec_module()` method
- add `Session.load_module(cache=True)` argument
- add `Directories` class which generates the paths to look for Python modules
  installed via Pip through PPYM and more
- entering the Node.py `Context` now adds the local `nodepy_modules/.bin`
  directory to the `PATH` environment variable

### v0.0.10

- extensions are now checked in the order they are registered
- support loading bytecache files with the suffix `.cpython-XY.pyc`
- the `.py` loader now loads the respective bytecache file if appropriate
- `Context.register_binding()` now accepts arbitrary objects, not just
  `BaseModule` instances
- add `require.current` and `Context.current_module` properties
- support for `.nodepy-link` files as created by `ppym install -e`
- add `-v, --verbose` argument for debug prints when resolving module filenames
- use `argparse` instead of `click` due to problem with known arguments
  being consumed and not passed to the Node.py main module
- upgrade bundled PPYM to v0.0.8
- `setup.py develop` now passes `--develop` to `ppym/bootstrap`

### v0.0.9

- `setup.py` -- Fix creation of `node.py` script on Windows by hooking
  `distlib.scripts.ScriptMaker` (see issue #11)
- `require.main` property can now be set
- update bundled PPYM to v0.0.7
- `setup.py` now always upgrades to the bundled PPYM installation
