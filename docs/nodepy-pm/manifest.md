# nodepy-pm/lib/manifest

Parse package manifests.

```python
manifest = require('nodepy-pm/lib/manifest')
try:
  m = manifest.parse('package.json')
except (FileNotFoundError, manifest.InvalidPackageManifest) as exc:
  print(exc)
  m = None
```

  [SemVer]: http://semver.org/

## Specification

### `name`

*Required.* The name of the package. This may be a scope identifier
of the format `@scope/package-name`, or simply `package-name`. Allowed
characters for the scope and package name are digits, ASCII letters and `-_.`.

```json
{ "name": "@scope-name/package-name" }
```

### `version`

*Required.* A [SemVer] of the package's version.

```json
{ "version": "0.0.1-security" }
```

### `engines`

*Optional.* An object that maps engine-names to version numbers. These version
numbers should be [SemVer] too, but that is not a requirement. The actual
engine that runs the package will check the version number. The default engine
is `python` which compares against the Python version number.

TODO: PyPy, JPython, Stackless, etc. should match to different engine names.

```json
{
  "engines": {
    "python": ">=3.0.0"
  }
}
```

### `repository`

*Optional*. URL to the source code repository where the package is developed.
If specified, the URL must be valid.

```json
{ "repository": "https://github.com/nodepy/nodepy" }
```

### `license`

*Required when publishing a package on the registry.* The license of the
package source code.

```json
{ "license": "MIT" }
```

### `bin`

*Optional.* An object that associates script names with a request string
that is then executed as the main module when the script is executed.

```json
{
  "bin": {
    "manifest": "cli"
  }
}
```

### `scripts`

*Optional.* An object that associates event names with Node.py modules
which are executed during various events of the package lifecycle.

```json
{
  "scripts": {
    "post-install": "./bin/install.py",
    "pre-uninstall": "./bin/uninstall.py",
    "pre-dist": "./bin/dist.py"
  }
}
```

Currently supported fields are:

- pre-script
- pre-install, post-install
- pre-uninstall
- pre-dist, post-dist
- pre-publish, post-publish

__Todo__

- post-uninstall
- pre-version, post-version
- pre-test, test, post-test
- pre-stop, stop, post-stop
- pre-start, start, post-start
- pre-restart, restart, post-restart

### `private`

*Optional*. Prevent publication of the package with `nodepy-pm publish`. This is used
for packages that want to take advantage of the nodepy-pm dependency management but
are not actuall supposed to be placed into the public registry. An example
of this would be a package that generates the documentation of another project.

```json
{ "private": true }
```

### `main`

This field describes the name of the module to load when your package is
required by another module. If this field is not specified, the
`Context._index_files` are tried instead (which are `index` and `__init__`).

```json
{ "main": "main.py" }
```

### `dependencies`

*Optional.*: An object that specifies the dependencies of the package.
All values must be valid `nodepy-pm/lib/semver:Selector` syntax, Git URL syntax
of the format `git+<url>[@<ref>]` or relative paths of the format
`[-e] [./|../]<path>`. Dependencies declared here will be installed
transitively.

```json
{
  "dependencies": {
    "nodepy-pm": "~0.0.8",
    "nodepy-pm-registry": "~0.0.3",
    "some-module": "git+https://github.com/someuser/some-module.git@development",
    "local-module": "-e ../local-module"
  }
}
```

### `dev-dependencies`

*Optional*. Dependencies that are listed here are required only for developing
a package, thus they will only be installed when using `nodepy-pm install` without
additional arguments in the directory where the `package.json` file lives,
unless `--production` is specified. Also, development dependencies will not be
installed transitively.

```json
{
  "dev-dependencies": {
    "js-nodepy": "~0.0.2"
  }
}
```

### `python-dependencies`

*Optional.* Similar to the `dependencies` field, but it specifies actual
Python modules that the package requires. These modules can be installed
by [nodepy-pm] using [Pip].

```json
{
  "python-dependencies": {
    "Flask": "==0.12",
    "Flask-HTTPAuth": "==3.2.2",
    "mongoengine": "==0.11.0"
  }
}
```

### `dev-python-dependencies`

*Optional*. Python dependencies that are required for developing the package.
See the `dev-dependencies` field for when development dependencies are
installed.

```json
{
  "dev-python-dependencies": {
    "mkdocs": ">=0.16.1"
  }
}
```

### `dist`

*Optional*. An object that specifies options for generating an archived
distribution of the package with `nodepy-pm dist`.

```json
{
  "dist": {
    "include_files": [],
    "exclude_files": [".hg*"]
  }
}
```

#### `include_files`

*Optional.* A list of patterns that match the files to include.
Matching patterns include files possibly excluded by `exclude_files`.

#### `exclude_files`

*Optional.* A list of patterns that match the files to exclude from the
archive. Note that when installing packages with [nodepy-pm], it will add
default exclude patterns to this list. The actual patterns may change
with versions of nodepy-pm. When this document was last updated, nodepy-pm added
the following patterns:

- `.svn/*`
- `.git`
- `.git/*`
- `.DS_Store`
- `*.pyc`
- `*.pyo`
- `dist/*`
- `nodepy_modules/`

  [Pip]: https://pypi.python.org/pypi/pip
  [nodepy-pm]: https://github.com/nodepy/nodepy