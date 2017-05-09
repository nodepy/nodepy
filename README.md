<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# PPYM

PPYM is the [Node.py] package manager. Check out the [Docs].

  [Node.py]: https://github.com/nodepy/nodepy
  [Docs]: https://nodepy.github.io/nodepy/ppym/

__Installation__

PPYM is automatically installed with [Node.py]. If for some reason you have
Node.py installed without PPYM, use the `bootstrap.py` script.

    $ git clone https://github.com/nodepy/ppym.git
    $ node.py ppym/bootstrap --root --upgrade

## Changelog

### v0.0.18

- Fix #9 (partially): Pip install fails with FileNotFoundError: installed-files.txt
  -- added `lib/brewfix.py` which temporarily (over)writes `~/.pydistutils.cfg`,
  only fixes `--user` installs of Node.py (and installs in Virtualenv still
  work flawlessly, too)
- Fix `ppym install --save` saving version as `^VERSION` which is wrong,
  now uses `~VERSION`
- Fix `env:get_module_dist_info()` replacing hyphens by underscores, as Pip
  does it
- Better detection of module `.dist-info`

### v0.0.17

- Add `-P,--packagedir` option to `ppym install`
- Add `-I,--ignore-installed` option to `ppym install`
- Allow listing dependencies to local folders in `package.json` using
  `[-e] [./|../]<path>` syntax
- Fix nodepy/nodepy#23: Windows: Node.Py installed to `AppData\Local\Programs\Python` but
  PPYM to `~/.local/Scripts`: For Python installations inside the users home
  directory, `--global` will by default install to `sys.prefix` instead of
  `~/.local` (can still be overwritten with the `prefix` configuration option).
- Remove `ppym pip-install` command
- Add `ppym install` support for installing standard Python modules by
  prepending `py/`, for example `py/request`
- `--save` and `--save-deps` now also works with Python dependencies when
  the `py/<req>` format is used
- `ppym init`: Author and License fields are now optional and can be omitted
  by entering `-` if a default value is already available, or otherwise simply
  enter nothing
- add Description field to `ppym init`

### v0.0.16

- Hotfix for PPYM installation to the root directory

### v0.0.15

- remove caret (`^`) version selector from semver for now, it is not
  implemented the same as the Node.js NPM semver criteria semantics anyway
- Fix #10: Pip install can not access already installed local packages
- Add `pip-install` command
- Uppercase characters are now valid characters in a package name

### v0.0.14

- deduct pip install locations from pip module
- follow pip convention in writing the installed files to `installed-files.txt`
  rather than `.ppym-installed-files`. Note that PPYM will assume that such a
  file would not be part of a package.
- enhance Python 2 compatibility
- manifest `"bin"` fields may now end with `${py}` in which case the script
  is installed in three versions: plain, with the major Python version appended
  and with the major.minor Python version appended
- install PPYM as plain command, with major and major.minor version

### v0.0.13

- fix `ppym run` for Node.py scripts, `--current-dir` was placed after the
  actual script that was to be executed

### v0.0.12

- add support for install dependencies via Git URLs (like `git+https://gith...`)

### v0.0.11

- fix `is_virtualenv()` which returned True outside a virtual environment
- use `.git*` default exclude pattern, fix exclude patterns read from package
  manifest in `walk_package_files()`
- fix `ppym dist` which would not close the archive before returning, which
  caused `ppym publish` to upload an empty package archive
- add `ppym install --save/--save-dev` options
- add `ppym install --recursive` option

### v0.0.10

- fix `ppym run` for actual Node.py scripts, using `nodepy.main()` over
  `Require.exec_main()` to create a new Context with the correct `sys.path`
  setup
- update install locations and add `--root` flag to `ppym install` and
  `ppym uninstall`
- `-g,--global` will be upgraded to `--root` when inside a virtual env
- rebuilt `bootstrap.py` to use `argparse` instead of third-party `click` library

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
