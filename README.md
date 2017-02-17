# cpm

**cpm** is a package manager for Python3-ish modules. It was originally
intended as part of the [Craftr] build system.

## Project Goals

- [node.js]-style Python modules that can be loaded with `require()`
- [npm]-style dependency management
- Foundation for the [Craftr] build system


  [npm]: https://www.npmjs.com
  [node.js]: https://nodejs.org/en/
  [Craftr]: https://craftr.net
  [SemVer]: http://semver.org/

## Package Manifests

Similar to node.js modules, **cpm** packages require a `cpm.json` package
manifest file.

### Example

```json
{
  "name": "demo-app",
  "version": "1.0.0",
  "main": "index.py",
  "dependencies": {
    "exile": "~1.2.0"
  },
  "python-dependencies": {
    "requests": "==2.13.0",
    "glob2": "==0.4.1"
  },
  "scripts": {
    "demo-app": "index:main"
  }
}
```

### name

The name of the package. Valid identifiers consist of only ascii letters,
digits and the special characters `.-_` .

### version

A [SemVer] for the package.

### main

The main Python script to load when the package is required.

### dependencies

An object that specifies which other **cpm** packages are necessary for this
package. The values for each key must be a selector that specifies exactly one
or a range of version numbers.

### python-dependencies

Similar to the **dependencies** field, but the package names listed here are
installed using `pip install`. Note that here the values for each key must be
version specifiers that Pip understands!

### scripts

A dictionary that maps names of console-scripts to the name of a Python
script in this package and a function name as `<script>:<function>`. Note that
the `<script>` part is without the `.py` suffix.

Scripts will be installed globally under `~/.cpm/bin` and locally under
`cpm_modules/.bin`.
