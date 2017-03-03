<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# PPYM

PPYM is the [Node.py] package manager.

  [Node.py]: https://github.com/nodepy/nodepy

__Synopsis__

    ppym init                    (initialize a package.json)
    ppym dist                    (create a .tar.gz archive from the current package)
    ppym register                (register a new account on the package registry)
    ppym publish                 (create a package distro and upload to the registry)
    ppym upload <filename>       (upload a file to the package registry)
    ppym install [-g]            (install all dependencies of the current package)
    ppym install [-g] .          (install a package from a directory)
    ppym install [-g] <filename>
        (install a package from an archive)
    ppym install [-g] [@<scope>/]<package>
        (install a package from the PPYM package registry)
    ppym uninstall [-g] [@<scope>/]<package>
        (uninstall a previously installed package)
    ppym bin                      (print the path to the bin directory)

__Installation__

Use the `bootstrap.py` script to install PPYM.

    $ git clone https://github.com/nodepy/ppym.git
    $ node.py ppym/bootstrap --install --global

## Changelog

### v0.0.9

- add `ppym bin [-g]` which will print the path to the bin directory
- add `PackageManifest.run_script()`
- change `PackageManifest` constructor now validates the `name` parameter
- renamed `package.json` `"script"` field to `"scripts"` and change
  usecase for package lifecycle events instead of installing command-line
  scripts
- implement package lifecycle event scripts `pre-dist`, `post-dist`,
  `pre-install`, `post-install`, `post-uninstall`, `pre-publish` and
  `post-publish`
- `ppym upload` commamnd now warns you if you attempt to upload a file that
  appears to be a package distribution archive but does not match the
  current version of your project
- add `ppym publish` command

### v0.0.8

- add `--develop` option to `bootstrap.py`
