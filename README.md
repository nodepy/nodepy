# ppy-engine

**ppy** is intended to be somewhat of a Node.js clone for Python. It executes
Python modules with a `require()` function which can be used to load other
Python modules. A Python modules that provides a `package.json` manifest is
called a *package*.

**ppym** is the package manager similar to *npm*. It itself is a ppy Python
package that is globally available when **ppy** is installed.

The goal of this project is to develop a Python environment that can execute
Python code **free from global state**. I have come across problems with the
global interpreter state especially in Python plugin development.

## Synopsis

    ppy                         (enter interactive session)
    ppy <filename>              (run module file)
    ppy -p [@<scope>/]<package>[/<module>][:member]
        (run a package, specific module or even a specific function)

    ppym init                    (initialize a package.json)
    ppym dist                    (create a .tar.gz archive from the current package)
    ppym register                (register a new account on the package registry)
    ppym upload <filename>       (upload a file to the package registry)
    ppym install [-g]            (install all dependencies of the current package)
    ppym install [-g] .          (install a package from a directory)
    ppym install [-g] <filename>
        (install a package from an archive)
    ppym install [-g] [@<scope>/]<package>[@<version>]
        (install a package from the ppy registry)
    ppym uninstall [-g] [@<scope>/]<package>[@<version>]
        (uninstall a previously installed package)

## Packages

Packages are installed locally to the `ppy_packages/` directory of your
workspace. Global packages are installed into `~/.local/ppy_packages`
instead (note that you can change the prefix with the `ppy.prefix` config
value).

Package manfiests a JSON files with the following fields:

- `name` (required): The name of the package. This may be a scope identifier
  of the format `@scope/package-name`, or simply `package-name`. Allowed
  characters are digits, ASCII letters and `-_.`.
- `version` (required): A [SemVer] of the package's version.
- `engines` (required): An object that maps engine-names to version numbers.
  These version number should be [SemVer] too, but that is not a requirement.
  The actual engine that runs the package will check the version number. The
  default engine is `python` which compares against the Python version number.
  TODO: PyPy, JPython, Stackless, etc. should match to different engine names.
- `license` (required when uploading to the registry): The license of the
  package source code.
- `main`: The main Python module to run when the package is loaded. Defaults
  to `index.py`.
- `bin`: An object that describes names of command-line programs with `ppy -p`
  identifiers of the form `[[@<scope>/]<package>][/module][:member]` (the
  `<package>` part using the current package as default).
- `scripts`: Similar to the `bin` field, but the values for each script name
  must be a system command instead.
- `dependencies`: An object that maps ppy package names to version specifiers.
  The dependencies, if not already met, will be installed from the ppy
  package registry.
- `python-dependencies`: An object that maps *normal* Python package names
  to version specifiers that **Pip** understands. These dependencies will be
  installed into `ppy_packages/.pymodules` using `pip install`.
- `dist`: An object that specifies options for generating an archived
  distribution of the package source.

    - `include_files`: A list of patterns that match the files to include.
      Matching patterns exclude possibly excluded files with `exclude_files`.
    - `exclude_files`: A list of patterns that match the files to exclude
      from the archive.
