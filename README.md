<p align="center"><img src="https://i.imgur.com/fy4KZIW.png" height="128px"></p>
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img src="https://travis-ci.org/nodepy/nodepy.svg?branch=develop">
</p>

## Node.py

Node.py is a Python runtime and package manager compatible with CPython 2.7
and 3.3 &ndash; 3.6. It provides a separate but superior import mechanism for
modules, bringing dependency management and ease of deployment for Python
applications up to par with other languages, **without virtualenvs**.

Node.py comes with a built-in package manager that builds on Pip for standard
Python dependencies but also adds the capability to install packages that are
specifically developed for Node.py. To install the dependencies of the
package manager you must specify the `[pm]` install extra.

> Node.py is inspired by [Node.js](https://nodejs.org).

## Installation

    pip3 install nodepy-runtime[pm]

## Usage Example

Node.py allows you to write very modular Python applications with module
import semantics that are more easily trackable. From a language standpoint,
it is a superset of standard Python. It provides some syntactic sugar as well
as additional built-ins for scripts loaded with Node.py

| Built-in | Description |
| -------- | ----------- |
| `require` | An instance of the `Require` class created specificially your module. Allows you to load other modules like `require('./module')` |
| `module` | The `PythonModule` object that represents your Node.py module. |

| Concept | Description |
| ------- | ----------- |
| `if require.main == module:` | The Node.py way of saying `if __name__ == '__main__':`. |
| `import <...> from '<module-name>'` | Syntactic sugar for the `require()` built-in function. |
| `namespace <name>:` | Similar to a `class` declaration, but a module is created instead. |

__Example script__

```python
import flask
import sys
import cli from './cli'
require('werkzeug-reloader-patch').install()
app = flask.Flask('myapp')
import './models'
if require.main == module:
  sys.exit(cli.main())
```

__Example `nodepy.json`__

```json
{
  "name": "myapp",
  "pip_dependencies": {
    "Flask": ">=1.0.2",
    "pony": ">=0.7.3"
  },
  "dependencies": {
    "werkzeug-reloader-patch": "^0.0.7"
  }
}
```

## Troubleshooting

__FileNotFoundError: No such file or directory: '...\\installed-files.txt'__

This is a bug [that will be fixed with Pip 9.0.2](https://github.com/pypa/pip/issues/373#issuecomment-302632300).
In the meantime, to fix this issues, ensure that you have the `wheel` package
installed.

    pip3 install wheel [--user]

## Changes

### v2.1.6

* Fix duplicate execution of code specified with the `-c` option
* Add `namespace <name>:` declaration concept (`nodepy.extensions.NamespaceSyntax`)
* Merge `nppm` into the `nodepy` command-line

### v2.1.5 (2018-08-18)

* Add `Request.copy()` method

### v2.1.4 (2018-08-13)

* Handle relative package links (actually already in 2.1.3)

### v2.1.3 (2018-08-13)

* Fix `PythonLoader.suggest_files()`, no longer replaces an existing suffix
  when trying to add `.py` suffix

### v2.1.2 (2018-06-15)

* Fix `MANIFEST.in` which now includes `requirements.txt` (required by `setup.py`)

### v2.1.1 (2018-06-14)

* Release date fix for v2.1.0

### v2.1.0 (2018-06-14)

* Rename `nodepy-pm` to `nppm` in `README.md`
* Add MIT license to the header of all source files

### v2.0.3 (2018-06-03)

* The `nodepy.base.Module()` constructor now accepts absolute filenames only
* Update `setup.py` to include Markdown `long_description` and read install
  requirements from `requirements.txt`

### v2.0.2 (2018-03-30)

* The local `.nodepy/pip` directory is now always added to `sys.path` by using
  the `EntryModule.run_with_exec_handler()` method instead of loading
  and executing the module directly
* `PythonLoader.load()` no longer adds to `sys.path` if the path already is
  in the list

### v2.0.1 (2017-12-19)

* `PythonLoader._load_code()` now uses utf8 encoding by default, however we
  should try to peek into the file to see if it contains a coding: comment
* Always add local `modules_directory` to Context resolve path, this helps
  projects that use package links
* Node.py repl can now also import from `.nodepy/pip` directory
* Fix `resolve_root` outside of package root
* Don't import `pathlib` from `nodepy.utils.path`, but instead import
  `pathlib2` directly. We decided on not using std `pathlib` if it is
  available, as there can be minor differences
* Add missing `strict=False` to `UrlPath.resolve()` and `ZipPath.resolve()`
* Add info to `nodepy.runtime.scripts` that it can also holds an `args` member
* `resolve_root` now taken into account for default `Package.main` if it is
  not explicitly defined, add `resolve_root` when package entry point is required
* `StdResolver.package_for_directory()` must resolve the path to eliminate
  pardir elements, otherwise we can end up with two Packages pointing to the
  same directory, but one contains `subdir/..` elements
* Update `Module.name` property to be able to produce a requirable module name
  for modules outside a package's `resolve_root`
* Fixed comparing RequestString with actual request str in `Request.try_()`
  to properly raise TryResolveError
* Fix `FrameDebugger` parent calls for Python 2
* Add `Config.sections()`, remove debug print in `Context.__init__()`
* Remove `nodepy.default_context`, but add `nodepy.get_default_context()` instead
* Add `nodepy.utils.config` module and add `Context.config` member which is
  initialized from the `NODEPY_CONFIG` file or `~/.nodepy/config`

### v2.0.0 (2018-11-24)

* Complete rewrite
* Abstract module resolving interface
* Using the `pathlib2` module to abstract the filesystem

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
