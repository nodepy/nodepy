<img src="http://i.imgur.com/W3652bU.png" align="right"></img>
# @ppym/engine

This is Ppy (pronounced "Papaya"), a module-loader, built **in and for Python**,
that behaves quite similar to [Node.js]. It comes prebundled with PPYM, the
package manager that can install and manage Ppy packages from the [Ppy registry].
The goal of this project is to develop an environment that can execute Python
code **without global state** and which prefers local over global dependencies.

Unlike normal Python modules, Ppy modules are not stored in a global cache
like `sys.modules` by their name. Instead, they are stored on a session-level
and by their absolute filename. This allows many Ppy modules with the same
filename to be loaded. Also, there can be an arbitrary number of Ppy sessions
in the same process which are completely independent.

The Ppy package manager (`ppym`) *does* support standard Python modules and
can install them via Pip. Ppy uses [localimport] to restore a clean global
state after the program leaves the session context.

  [Pip]: https://pypi.python.org/pypi/pip
  [ppym]: https://github.com/ppym/ppym
  [Node.js]: https://nodejs.org/en/
  [Ppy registry]: https://github.com/ppym/registry
  [localimport]: https://github.com/NiklasRosenstein/py-localimport

## Synopsis

    ppy                         (enter interactive session)
    ppy <request>               (resolve request into a filename and run
                                 it as a Python script in the ppy environment)

## Example

```
$ ls
index.py utils.py ppy_modules/
$ cat index.py
```
```python
manifest = require('@ppym/manifest')
utils = require('./utils')
if require.is_main:
  utils.print_manifest_info(manifest.parse('package.json'))
```
```
$ ppy index
Information on manifest of package "demo-app@1.0.0"
- Filename: package.json
- Directory: .
- License: MIT
[...]
```

## Additional Links

- [@ppym/ppym][ppym]
- [@ppym/registry][Ppy registry]
