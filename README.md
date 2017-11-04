<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
<h1 align="center">Node.py (WIP)</h1>
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img src="https://travis-ci.org/nodepy/nodepy.svg?branch=develop">
</p>
<p align="center">
  A Node.js-like runtime for Python.
</p>

### Installation

From Git:

    $ pip install git+https://github.com/nodepy/nodepy.git@develop

### Packages

  [Node.py PM]: https://github.com/nodepy/nodepy-pm

Node.py has its [own package manager][Node.py PM]. Similar to Node.js,
packages are installed into a local modules directory (`./.nodepy_modules`).
It supports the installation of PyPI packages to this modules directory
as well.

To install `nodepypm`:

    $ nodepy https://nodepy.org/install-pm

Append the `-g` flag if you installed Node.py with the Pip `--user` flag.

The Node.py runtime understands only a small part of the package ecosystem.
It will parse package manifests (`nodepy.json`) when executing Python scripts
and importing other modules from other packages. That information is only used
to determine the main entry point for a package and the directory that module
requests are resolved in.

```json
{
  "name": "mypackage",
  "version": "1.13.3",
  "resolve_root": "./lib",
  "main": "./lib/index.py"
}
```

### Running Scripts

The `nodepy` command-line allows you to use a REPL or run a Python script.
Node.py can load and execute all standard Python scripts, only that such
scripts will then have access to Node.py's additional built-ins, such as the
`require()` function and the specialized `import` syntax.

```python
import {hello} from './hello'   # same as: hello = require('./hello').hello

if require.main == module:
  hello('John')
```

> Note that in Node.py we test for `require.main == module` instead of
> `__name__ == '__main__'`. If you want to run a standard Python script
> that tests for `__name__` with Node.py, you need to pass the `--pymain`
> argument, like
>
>     $ nodepy --pymain myscript.py

### Built-ins

#### `require`

Every module has it's own copy of the `require()` function, which is actually
an instance of the `nodepy.context.Require` class. The `require()` function
takes the following arguments:

* request (str) &ndash; A string that can be used to find another module.
  That module will be loaded and it's namespace or exported member
  (`Module.exports`) will be returned.
* exports (bool) &ndash; `True` by default. If this argument is `False`, the
  actual `nodepy.base.Module` object will be returned instead of its namespace
  or exported member.

#### `require.main`

The module that is executed via the command-line as the main module. This
module is supposed to behave as being invoked as a program. Modules that
support execution as a program are supposed to check if they are the chosen
module:

```python
if require.main == module:
  main()
```

#### `module`

The `nodepy.base.Module` object for this file. The `module.namespace` object
is the Python module object in which the file is executed.

```python
assert globals() is vars(module.namespace)
```

#### `module.filename`, `module.directory`

A `pathlib2.Path` instance that resembles the filename or directory of the
module, respectively. A module could be loaded not directly from the
filesystem but instead, for example, an internet resource or ZIP file. You
should load resources not using the Python `open()` function or the `os`
module, but instead by starting from the `module.directory` Path object.

### Todolist

* Python bytecache loading/writing
* Node.js-style traceback (Python's traceback sucks)
