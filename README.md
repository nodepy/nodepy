<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# PPYM

PPYM is the [Node.py] package manager. Check out the [Docs].

  [Node.py]: https://github.com/nodepy/nodepy
  [Docs]: https://nodepy.github.io/nodepy/ppym/

__Installation__

PPYM is automatically installed with [Node.py]. If for some reason you have
Node.py installed without PPYM, use the `bootstrap.py` script.

    $ git clone https://github.com/nodepy/ppym.git
    $ node.py ppym/bootstrap --install --global

## Changelog

### v0.0.10

- fix `ppym run` for actual Node.py scripts, using `nodepy.main()` over
  `Require.exec_main()` to create a new Context with the correct `sys.path`
  setup
- update install locations and add `--root` flag to `ppym install` and
  `ppym uninstall`
- `-g,--global` will be upgraded to `--root` when inside a virtual env

### v0.0.9

- add `ppym bin [-g]` which will print the path to the bin directory
- add `PackageManifest.run_script()`
- change `PackageManifest` constructor now validates the `name` parameter
- renamed `package.json` `"script"` field to `"scripts"` and change
  usecase for package lifecycle events instead of installing command-line
  scripts
- implement package lifecycle event scripts `pre-dist`, `post-dist`,
  `pre-install`, `post-install`, `post-uninstall`, `pre-publish`,
  `post-publish` and `pre-script`
- `ppym upload` commamnd now warns you if you attempt to upload a file that
  appears to be a package distribution archive but does not match the
  current version of your project
- add `ppym publish` command
- PPYM no longer installs scripts into the Bin directory of the Python prefix
  in virtual envs, but instead always into `nodepy_modules/.bin` (see the
  output of `ppym bin` or `ppym bin --global` for information on what that
  path is)
- add `script:make_environment_wrapped_script()`
- add `Installer.relink_pip_scripts()`
- PPYM will now attempt to wrap scripts installed by Pip into the Pip bin
  directory (see `ppym bin --pip [--global]`) and create a proxy in the
  `nodepy_modules/.bin` directory
- Scripts installed via the `"bin"` field are now automatically appended with
  `.py` if they don't already end it `.py` or `.pyw`. This is to prevent
  `distlib` from stripping any extension that is intended to be in the scripts
  call name. (Windows only)
- add `"private"` field to the manifest specification
- remove `"postinstall"` field from the manifest specification (backwards
  incompatible)
- add `"dev-dependencies"` and `"dev-python-dependencies"` fields to manifest
- add `ppym run <script>` command
- all commands that are based on information provided in `package.json` now
  search for it in parent-directories, thus you can now use `ppym run`,
  `ppym dist`, `ppym publish` etc. from sub-directories in your project

### v0.0.8

- add `--develop` option to `bootstrap.py`
