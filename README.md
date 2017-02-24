# upython

**upython** is a runner for Python scripts that provides a mechanism to load
packages with `require()`. Packages are managed with **upm**. The key concept
is derived from *Node.js* and *npm*.

## Todo

- Implemented `upm init, ls`
- Implemented a browsable web-interface for `upmd`
- Make `upython` compatible with Python 2.7+ and Python 3.3+ (currently
  tested on Python 3.5 only)

## Synopsis

    [x] upython
    [x] upython <script>.py
    [x] upython -p <package>[@<version>][/<module>]
    [x] upm install [-g] .
    [x] upm install [-g] <archive>
    [x] upm install [-g] <package>[@<version>]
    [x] upm uninstall [-g] <package>
    [x] upm init
    [ ] upm ls
    [x] upm dist
    [x] upm register
    [/] upm upload <filename>
    [/] upmd [-h] [-p] [-d] [--prefix]

## Packages

**upm** can install packages locally into the `upython_packages/` directory or
globally into `~/.upython/packages` from a remote registry or from an existing
package directory. Similar to *Node.js*, packages in **upython** require a manifest.

When a package is ready to be made publicly available, it can be uploaded to
the package registry. First it needs to be regsitered, then a distributable
package archive must be created, which can be then be uploaded.

Example manifest:

```json
{
  "name": "demo-app",
  "version": "1.0.0",
  "main": "index.py",
  "engines": {
    "python": ">=3.0.0"
  },
  "bin": {
    "demo-app": "index.py"
  },
  "scripts": {
    "say-hello": "echo \"Hello!\""
  },
  "dependencies": {
    "exile": "~1.2.0"
  },
  "python-dependencies": {
    "requests": "==2.13.0",
    "glob2": "==0.4.1"
  },
  "dist": {
    "include_files": ["README.md", "*.py", "public/*"]
  },
  "postinstall": "postinstall.py"
}
```

## Registry Server

**upmd** is the upython registry server that can be set-up anywhere you want.
The global registry is available at [upmpy.org]. To install the **upmd**
requirements, use `pip install upython[upmd]`.

__Requirements__

- Python 3.5 or newer
- MongoDB

  [upmpy.org]: https://upmpy.org/

## Configuring upython & upm

The upython configuration file lives in `~/.upython/config`. By settings the
`UPYTHON_CONFIG` environment variable, this default file location can be
changed. You can find the default values below.

```ini
[upython]
prefix = ~/.upython
local_packages_dir = upython_packages

[upm]
registry = https://upmpy.org/
author =
license =

[upmd]
host = localhost
port = 8000
visible_host = %(host):%(port)
visible_url_scheme = http
debug = false
prefix = ~/.upython/registry
mongodb_host = localhost
mongodb_port = 27017
mongodb_database = upm_registry
email_origin = no-reply@upmpy.org
email_smtp_host = localhost
email_smtp_ssl = false
```
