# install

```
ppym install [-g,--global] [--root] [-e,--develop] [--pip-separate-process]
             [--dev/--production] [PACKAGES]
```

Installs one or more Node.py packages from the PPYM registry, package
distribution files (see [`ppym dist`](dist)) or a directory. If no PACKAGES
are specified, the dependencies of the current package are installed. In that
case, the `--dev` switch is enabled by default, otherwise `--production` is
the default.

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
