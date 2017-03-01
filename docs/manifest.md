# ppym/lib/manifest

Parse package manifests.

```python
manifest = require('ppym/lib/manifest')
try:
  m = manifest.parse('package.json')
except (FileNotFoundError, manifest.InvalidPackageManifest) as exc:
  print(exc)
  m = None
```

## Specification

### `name`

*Required.* The name of the package. This may be a scope identifier
of the format `@scope/package-name`, or simply `package-name`. Allowed
characters for the scope and package name are digits, ASCII letters and `-_.`.

```json
  "name": "@ppym/manifest"
```

### `version`

*Required.* A [SemVer] of the package's version.

```json
  "version": "0.0.1-security"
```

### `engines`

*Optional.* An object that maps engine-names to version numbers. These version
numbers should be [SemVer] too, but that is not a requirement. The actual
engine that runs the package will check the version number. The default engine
is `python` which compares against the Python version number.

TODO: PyPy, JPython, Stackless, etc. should match to different engine names.

```json
  "engines": {
    "python": ">=3.0.0"
  }
```

### `repository`

*Optional*. URL to the source code repository where the package is developed.
If specified, the URL must be valid.

### `license`

*Required when publishing a package on the registry.* The license of the
package source code.

```json
  "license": "MIT"
```

### `main`

*Optional.* The main Python module to run when the package is loaded.
Defaults to `index`.

```json
  "main": "cli"
```

### `bin`

*Optional.* An object that associates script names with a request string
that is then executed as the main module when the script is executed.

```json
  "bin": {
    "manifest": "cli"
  }
```

### `script`

*Optional.* Similar to the `bin` field, only that it maps script names to
shell commands.

```json
  "script": {
    "say-hello": "echo \"Hello $USER\""
  }
```

### `dependencies`

*Optional.*: An object that specifies the dependencies of the package.
All values must be valid `@ppym/semver:Selector` syntax.

```json
  "dependencies": {
    "@ppym/refstring": "~0.0.1",
    "@ppym/semver": "~0.0.1"
  }
```

### `python-dependencies`

*Optional.* Similar to the `dependencies` field, but it specifies actual
Python modules that the package requires. These modules can be installed
by [ppym] using [Pip].

```json
  "python-dependencies": {
    "Flask": "==0.12",
    "Flask-HTTPAuth": "==3.2.2",
    "mongoengine": "==0.11.0"
  }
```

### `dist`

*Optional*. An object that specifies options for generating an archived
distribution of the package with `ppym dist`.

```json
  "dist": {
    "include_files": [],
    "exclude_files": [".hg*"]
  }
```

#### `include_files`

*Optional.* A list of patterns that match the files to include.
Matching patterns include files possibly excluded by `exclude_files`.

#### `exclude_files`

*Optional.* A list of patterns that match the files to exclude from the
archive. Note that when installing packages with [ppym], it will add
default exclude patterns to this list. The actual patterns may change
with versions of ppym. When this document was last updated, ppym added
the following patterns:

- `.svn/*`
- `.git`
- `.git/*`
- `.DS_Store`
- `*.pyc`
- `*.pyo`
- `dist/*`
- `ppy_modules/`


  [Pip]: https://pypi.python.org/pypi/pip
  [ppym]: https://github.com/ppym/ppym

## Changelog

### v0.0.2

- Added `repository` field
