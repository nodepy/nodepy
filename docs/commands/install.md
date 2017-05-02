# install

```
ppym install [-g,--global] [--root] [-e,--develop] [-P,--packagedir]
             [--pip-separate-process] [--dev/--production] [--save]
             [--save-dev] [--recursive] [PACKAGES]
```

Installs one or more Node.py packages from the PPYM registry, package
distribution files (see [`ppym dist`](dist)) or a directory. If no PACKAGES
are specified, the dependencies of the current package are installed. In that
case, the `--dev` switch is enabled by default, otherwise `--production` is
the default.

The *PACKAGES* argument, if specified, can be of the following type:

- A package name and version selector of the format `<package>[@<version>]`,
  in which case the package will be looked up and installed from the PPYM
  registry.
- An existing directory that contains a `package.json` to install from.
- A Git URL in the format `git+<url>[@<ref>]` to install the package from.

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
