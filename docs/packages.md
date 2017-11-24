# Node.py Packages

  [1]: https://github.com/nodepy/nodepy-pm

Node.py has its [own package manager][1]. Similar to Node.js, packages are
installed into a local modules directory (`./.nodepy_modules`). It supports
the installation of PyPI packages to this modules directory as well.

The Node.py runtime understands only a small part of the package ecosystem.
It will parse package manifests (`nodepy.json`) when executing Python
scripts and importing other modules from other packages. That information is
only used to determine the main entry point for a package and the directory
that module requests are resolved in.

Example `nodepy.json`:

```json
{
  "name": "mypackage",
  "version": "1.13.3",
  "resolve_root": "./lib",
  "main": "./lib/index.py"
}
```

Check out the [nodepy-pm Documentation][1] for more information on packages.
