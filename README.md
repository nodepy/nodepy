<p align="center"><img src="https://i.imgur.com/fy4KZIW.png" height="128px"></p>
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img src="https://travis-ci.org/nodepy/nodepy.svg?branch=develop">
</p>

## Node.py

Node.py is a Python runtime compatible with CPython 2.7 and 3.3 &ndash; 3.6.
It provides a separate but superior import mechanism for modules, bringing
dependency management and ease of deployment for Python applications up to par
with other languages, **without virtualenvs**.

> Node.py is inspired by [Node.js](https://nodejs.org).

**nppm** is Node.py's package manager that allows you to install and manage
standard Python packages (using Pip under the hood) *as well* as Node.py
packages without the hazzle of virtual environments. **nppm** is a powerful
tool for deploying Node.py applications and command-line tools. You can find
the nppm repository [here](https://github.com/nodepy/nppm).

## Usage Example

Node.py allows you to write very modular Python applications with module
import semantics that are more easily trackable. It also does not have the
concept of a separate `__main__` module as standard Python does. Any valid
Python script is a valid Node.py script.

```
$ ls
app.py models.py nodepy.json
$ head app.py
import flask
import * from './models'  # Node.py special syntax
require('werkzeug-reloader-patch').install()  # Node.py require() function
app = flask.Flask('myapp')
# ...
$ cat nodepy.json
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
$ nppm install
$ nodepy app
... Starting Flask server at localhost:8000
```

## Installation

Node.py is available from PyPI as `nodepy-runtime`. The Python version that
you install it into will also be the Python version that you will use in your
Node.py code.

> Tip: Add the `--user` flag if you don't want to install Node.py system-wide.

    $ pip install nodepy-runtime

There are multiple ways of installing **nppm**. The suggested method is to
use the remote install script. If you want to install a specific version,
pass the Git ref as an argument (eg. `develop` or `v2.0.2`). If you don't
specify a tag, the highest tagged version will be installed.

    $ nodepy https://nodepy.org/get-nppm.py

Alternatively, you can clone the repository and use the local install script.

    $ git clone https://github.com/nodepy/nppm.git
    $ nodepy nppm/scripts/install.py

> Important: The installer is **not** able to automatically detect whether
> Node.py was installed system-wide or with the `--user` option. If you
> installed Node.py with the `--user` option, pass the `--global` option to
> the install-script (global meaning user-location). The default is to install
> with `--root` (system-wide).

## Changes

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
