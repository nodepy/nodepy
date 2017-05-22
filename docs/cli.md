**nodepy-pm** is the [Node.py] package manager.

  [Node.py]: https://github.com/nodepy/nodepy

__Synopsis__

    nodepy-pm bin
    nodepy-pm dist
    nodepy-pm init
    nodepy-pm install
    nodepy-pm publish
    nodepy-pm register
    nodepy-pm run
    nodepy-pm uninstall
    nodepy-pm upload

## bin

```
nodepy-pm bin [--global] [--pip]
```

Prints the local or global binary directory that **nodepy-pm** installs to. If
you pass the `--pip` switch, the Pip binary directory will be printed instead.

Note that [`nodepy-pm install`](install) will automatically create wrappers in
the Node.py binary directory that reference respective commands in the Pip
binary directory, thus if you have Python dependencies that expose scripts,
you only need to add the Node.py binary directory to your path.

The local binary directory is `nodepy_modules/.bin`.

---

## dist

```
nodepy-pm dist
```

Create a `.tar.gz` archive from your package and save it into the `dist/`
directory. If you want to publish the package on the registry, use the
[`nodepy-pm publish`](publish) command.

---

## init

```
nodepy-pm init
```

Initialize a `package.json` file in the current working directory.

---

## install

```
nodepy-pm install [-g,--global] [--root] [-e,--develop] [-P,--packagedir]
             [-I,--ignore-installed]
             [--pip-separate-process] [--dev/--production] [--save]
             [--save-dev] [--recursive] [PACKAGES]
```

Installs one or more Node.py packages from the package registry, package
distribution files (see [`nodepy-pm dist`](dist)) or a directory. If no PACKAGES
are specified, the dependencies of the current package are installed. In that
case, the `--dev` switch is enabled by default, otherwise `--production` is
the default.

The *PACKAGES* argument, if specified, can be of the following type:

- A package name and version selector of the format `<package>[@<version>]`,
  in which case the package will be looked up and installed from the package
  registry.
- An existing directory that contains a `package.json` to install from.
- A Git URL in the format `git+<url>[@<ref>]` to install the package from.
- A Python package requirement in the format `py/<req>`

With `--dev` enabled, the development dependencies of the packages are
installed additionally to their normal runtime dependencies. Note that
development dependencies are never installed transitively.

Using `--global` will install the PACKAGES into the user-global modules directory
and creates scripts in the global binaries directory. Note that "global" always
refers to the "User-space global". Global installations are only supposed to
be used for command-line tools. Node.py will not look to resolve `require()`s
in the global modules directory for your local project.

The `--root` option will install the package into the global Python prefix and
should only be used when a command-line utility should be installed for all
users of a system.

> Note: Inside a virtual environment, `-g,--global` will be promoted to `--root`.

The `--develop` flag can only be used when installing a package from a
directory. Using this flag will install the package in development mode, which
means that a `.nodepy-link` file will be created instead of the package
contents being copied. Node.py will read this link and continue resolving
`require()`s in the target directory (which is your package that you installed
with `--develop`).

The `-I,--ignore-installed` option will be passed to `pip install`.

The `-P,--packagedir` option can be used to change the directory from which
the `package.json` will be read (in case of an installation without packages
specified on the command-line) or written to (in case of `--save` and
`--save-dev`).

Using the `--save` or `--save-dev` options requires a `package.json` in the
current working directory to which the new dependencies can be added. Note
also that the package manifest will be re-written with a strict 2-space
indentation.

The `--recursive` option can be used to make sure dependencies of already
satisfied dependencies are satisfied as well. This can be useful if you
uninstall a dependencies of another package and want to re-install them
without remembering them all.

---

## publish

```
nodepy-pm publish [-f,--force] [-u,--user] [-p,--password]
```

A combination of [`nodepy-pm dist`](dist) and [`nodepy-pm upload`](upload) that also
invokes the `pre-publish` and `post-publish` [scripts](run).

__Requirements__

In order to publish a package to [ppym.org](https://ppym.org), it must
meet the following requirements:

- The `name` of the package must be scoped with your username (ie. `@username/packagename`)
- The `license` field in `package.json` must not be empty

After a package version has been uploaded to the registry, arbitrary files
may be uploaded to that version as well. This is intended to be used for
additional files that may be downloaded by the actual package when necessary.
Note that https://ppym.org currently has a size upload limit of 2MiB.

It is important that you read and understand the [PPYM Registry Terms of Use][0]
before you publish packages and upload content to the registry.

  [0]: https://ppym.org/terms

---

## register

```
nodepy-pm register [--agree-tos] [--save]
```

Register a new account on the package registry. Note that you can change the
URL to the registry being used in the `~/.ppymrc` file. By default, it will
point to https://ppym.org.

    $ cat ~/.ppymrc
    registry=http://localhost:8000

---

## run

```
nodepy-pm run SCRIPT [ARGS]
```

Runs the SCRIPT that is specified in the current package's manifest. Note that
some scripts have special meanings and will be invoked automatically by other
actions of the package manager (eg. `post-install` or `pre-publish`).

__Example__

```json
{
  "scripts": {
    "build-docs": "!mkdocs build",
    "pre-publish": "scripts/pre-publish.py"
  }
}
```

    $ nodepy-pm run build-docs

---

## uninstall

```
nodepy-pm uninstall [-g,--global] PACKAGES
```

Uninstalls one or more previously installed PACKAGES.

---

## upload

```
nodepy-pm upload [-f, --force] [-u, --user] [-p, --password] FILENAME
```

For the current version that is specified in the `package.json` of your
project, uploads the specified FILENAME to the package registry. If the
version and/or package does not exist at the time of the upload, the file
will be rejected unless you upload the distribution archive created with
[`nodepy-pm dist`](dist) first. If you upload the distribution archive, the
package and package version will be created and assigned to your account.

> __Note__: You should prefer to use the [`nodepy-pm publish`](publish) command
> to publish your package as it is less error prone and will also invoke
> the `pre-publish` script if you have one specified in your package manifest.

Read about the [Requirements](publish#requirements) to publish a package.
