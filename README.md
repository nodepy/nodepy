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

### v0.0.17

- rename `InteractiveSessionModule` to `InitModule`
- add `-P,--preload` option
- add `nodepy.get_python_library_path()`
- add `doraise=True` to `py_compile.compile()` call

### v0.0.16

- fix `require('.')` and `require('..')` being resolved in the PATH rather
  then relative to the current directory
- add `BaseModule.parent` and `BaseModule.request`
- add `Context.event_handlers` and `Context.send_event()`
- events `load`, `require` and `enter` are now sent via `Context.event_handlers`
- add `Require.cache`
- add `'__init__'` to `Context.index_files`, `'index'` might get deprecated
  in the future

### v0.0.15

- fix interactive Node.py session (NameError variable `code`)
- now install multiple versions of the `node.py` command for the Python
  version, eg. `node.py3` and `node.py3.5` for Python 3.5
- fix #17: Requiring another package from a develop install does not resolve
  in the original installation directory
- add `Context.resolve(followed_from)` and `Context.load_module(followed_from)`
- add `Context.resolve_and_load()` which automatically adds an element to
  `Require.path` for package links
- add `Require.path`
- add `BaseModule.require`
- remove `UnknownModuleTypeError` for now, `Context.load_module()` now raises
  a `ValueError` if no loader could be determined
- add `Context(bare=False)` parameter
- rename `NodepyModule` to `PythonModule`
- remove `NodepyByteModule`
- add `PythonModule(code)` parameter
- add `get_python_library_base()`
- replace `_py_loader()` function with `PythonLoader` class
- the `PythonLoader` class now writes a bytecache from the source file if
  `PYTHONDONTWRITEBYTECODE` is not set

### v0.0.14

- add nice string representation of `ResolveError`
- Python modules loaded with `require()` no longer inherit Node.py's future flags
- upgrade PPYM to v0.0.13

### v0.0.13

- `setup.py` installs PPYM into user directory if Node.py is installed
  into user directory
- add `--keep-arg0` argument to `node.py`, which is used when PPYM installs
  a command-line script
- `Context.load_module()` now accepts an explicit `loader` argument
- add `Context.get_extension()`
- add `Context.current_modules`
- always add local `nodepy_modules/` directory to `Context.path`
- add `Require.hide_main()`
- `exports` argument to `Require.__call__()`
- add `Context.register_index_file()`

### v0.0.12

- remove `nodepy.Directories` class again, we only need to compute the
  local `nodepy_modules/.pip` library directory
- entering `Context` no longer adds to `PATH`
- upgrade bundled PPYM to v0.0.10
- `setup.py` no longer installs PPYM dependencies
- 12a: Re-add `install_deps()` to `setup.py`, we need to make sure our
  dependencies are installed before PPYM can be bootstrapped

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
