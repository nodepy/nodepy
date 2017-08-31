+++
title = "Changelog"
ordering-priority = 5
+++

### v0.0.22

__Node.py__

- Added `Require.exec_main(inherit_path)` parameter
- Add new Context-event "leave" (`Context.Event_Leave`)
- Add `Context.Event_Require`, `.Event_Load`, `.Event_Enter` and `.Event_Leave`
  which are the event IDs that can be received by `Context.event_handlers`
- Fix #67 -- Skip bytecache file if not readable
- Remove `Require.subprocess()` and `Require.subprocess_args()`
- Add `Require.resolve()`
- No longer augments `nodepy.executable` and `nodepy.proc_args` when
  `nodepy.script` is set. This resolves an issue when trying to create a
  subprocess from `nodepy.proc_args` from inside an installed script.
- Add support for a "`resolve_root"` in the `FilesystemResolver`
- Removed `Session.get_package_from_directory()`
- Add 127 exit-code when exception occurs

__NPPM__

- Added `PYTHONPATH` back in commands and wrapper scripts, NOT in programs
  created from other Node.py applications

### v0.0.21

__Node.py__

- Fix #35 -- Code-objects loaded from bytecache have filename of temporary file 
- Fix #47 -- `Context.__enter__()` should return self
- Fix #48 -- Pip Install on Windows: Underlying buffer has been detached
- Fix #49 -- Importing local Python packages should be preferred over globally installed packages
- `nodepy.print_exc()` now tolerates `sys.stderr` not having an `isatty()` member
- Support `import * from 'module-name'` syntax with `!require-import-syntax` extension
- Support `# nodepy-extensions: ...` special comment in Python file headers
- Fix #56: "as" in member name when using require-import-syntax extension
  causes SyntaxError
- `Context.enter_module()` now catches potential `ValueError` when removing
  a path from `sys.path`
- Add `ExtensionHandlerRunner` class and the way extensions are invoked
- Add `BaseModule.extensions` property
- Replace `Package.get_extensions()` with `Package.extensions` member
- Fix `-L,--loader` option since `Context.get_loader()` was changed
- Implement #53 -- Add pluggable interface for resolving require() requests
  - Full restructure of the resolve and loading process, now similar to Python
    Import Hook mechanism
  - Rename `Context._get_package()` to `Context.get_package()` (now public)
  - Rename `Context._get_package_main()` to `Context.get_package_main()` (now public)
  - Add `Context.get_package_for()`
  - Update `Context.resolve()`, `Context.load_module()` and `Context.resolve_and_load()`
    drastically
  - Add `BaseResolver` class
  - Change `BaseLoader` class
  - Add `FilesystemResolver` class
  - Add `FilesystemLoaderSupport` class
  - Add `PythonFilesystemLoaderSupport` class
  - Add `JsonFilesystemLoaderSupport` class
  - Update `PythonLoader` class
  - Update `JsonLoader` class
  - Add `Request` class
- Remove `BaseModule.parent` member and turn it into a property, since the 
  parent module is now contained in the `BaseModule.request` object
- `BaseModule.request` is now a `Request` object instead of a string
- Replace `Request.followed_from` with `Request.original_resolve_location`
- Add `FilesystemResolver.cache` which helps enhance performance by about 5%
  (was hoping for more..)
- `-d,--debug` option can now be set to True with the environment variable
  `NODEPY_DEBUG=true`
- Fix post-mortem debugging
- Support `vendor-directories` in package manifest
- Add `nodepy.normpath()`
- Add `Context._package_stack`
- Add support for `import default_member, * from 'module-name'` syntax
- Add `nodepy.notebook_context()` function
- Add `Context.options`, and first option being supported is `require.autoreload`
- Update `BaseModule` interface
  - Add `exec_mtime` member
  - Add `reload()` method
  - Abstract method `exec_()` must now be called by subclasses
  - Add `source_changed` property
- Update `PythonLoader` so that `PythonModule.reload()` actually works and does
  not execute the old code
- Add `nodepy.script` member which will initialized by scripts that are
  installed via NPPM
- Add `nodepy.reload_pkg_resources(name='pkg_resources')`
- `require-import-syntax` extension now supports assigning imported names as
  members to existing objects in the scope

__nppm__

- Add `nppm version` command
- `@nodepy/nppm/lib/env:get_module_dist_info()` -- Added keys `.dist-info`
  and `top_level` to the returned dictionary
- `-e,--develop` option now requires a `PACKAGE` argument
- `-U,--upgrade` is now passed on to Pip
- Pip packages can now be installed from a directory and with the `-e` option
- Add `-py,--python` and `-epy,--develop-python` arguments in faviour of
  the `py/` package prefix
- Normalize package install locations, Pip packages are now always installed
  under `nodepy_modules/.pip`, even for `-g,--global` and `--root` installations
- Add `nppm dirs` command
- Files passed to `-py` argument are now passed directly to the Pip command-line
- Now prints the location scripts are installed to during the installation
- Fix `NameError: FileNotFoundError` in `nppm` on Python 2
- Fix #40 -- Ignore .py scripts when wrapping Pip installed scripts, or handle
  them properly
- Configuration file is now parsed with `configparser.SafeConfigParser`
- Implement #26 -- Support multiple package registries
- Fix error that was NOT raised when package was found but the archive was
  missing on the server
- Add `-F,--from` option to `nppm install`
- Add `REGISTRY` argument to `nppm register`
- Implement #27 -- Add `--to` option to `nppm upload` and `nppm publish`
- Implement #51 -- Support `vendor-directories` in package manifest
- Fix #59 -- Reloading pkg_resources can lead it to wrongly assume Python 2 instead of 3
- Fix #62 -- Installed scripts no longer export `PYTHONPATH`
- `ScriptMaker` now requires a `location` parameter
- Fix #60 -- Nppm must not consider Python dependencies installed for global
  packages when installing local dependencies
- `nppm install` with no arguments will now install the current directory in
  develop mode (thus, as a package links), including programs specified in
  the manifest's `"bin"` field
- Fix #65 -- Installing from Git now actually copies the whole Git directory
  to the install location instead of installing *from* a temporary directory

### v0.0.20

__nodepy__

- Fix `nodepy.proc_args` to contain `sys.executable` if the nodepy executable
  is not an `.exe` on Windows
- Fix #36: pkg_resources DistributionNotFound for packages installed with nppm
- If Pygments is available, will be used to print colored exception tracebacks
- Add instead `Context.loaders` and `Context.get_loader()`
- Fix missing import of `errno` module (causes exception when bytecache file
  can not be written due to eg. permission errors)
- Fix #41 -- Now uses `colorama.init()` if the colorama module is available.
  If not, and the current platform is Windows, colorized traceback output
  is disabled.
- Add ability to do `require('./package.json')` or with any other JSON file
- Implement #42 -- Support a `"main"` field in `package.json`
- Add an `"extensions"` field to `package.json`, currently supported extension
  event callbacks are `init_extension()` and `module_loaded()`
- Every module that is being executed is now associated with its nearest
  `package.json` through its `BaseModule.package` member.
- Remove `-v,--verbose` option and `Context.debug()` for now, needs to be
  reimplemented completely with actually useful and well formatted information
- `Context.binding()` now raises a `NoSuchBindingError`
- `require()` requests beginning with an `!` (exclamation mark) will be
  forwarded to `Context.binding()` (without the exclamation mark)
- Add `require-unpack-syntax` binding to `Context` class, which can be added
  to the extensions listed in a `package.json` manifest
- Add `require-import-syntax` binding to `Context` class, which can be added
  to the extensions listed in a `package.json` manifest
- `nodepy --version` now prints Python implementation name
- Add `--profile FILENAME` argument that will save a profile of the execution
  to the specified file.
- Fix issue with reloading `pkg_resources` module when the Node.py `Context`
  exits, when another module has changed or reloaded the module already.
- Add `wheel` as a dependency for Node.py
- Add `--isolated` command-line option (not usually necessary)
- Default has switched to non-isolated mode
- `nppm run` can now invoke programs in the nearest `nodepy_modules/`
  directory if the command is not already captured by a script defined
  in the package manifest

__nodepy internal__

- Remove `Context.register_extension()` and `Context.get_extension()`
- Add `BaseModule.real_filename` as `BaseModule.filename` must always match
  the filename that was passed into the loader (otherwise `BaseModule.remove()`
  does not work)
- Add `JsonLoader` class
- Add `PythonLoader(support_require_unpack_syntax)` argument
- Remove `nodepy.get_python_library_base()` and `nodepy.get_python_library_path()`
- Add `nodepy.get_site_packages()` instead
- Add `nodepy.Package` class
- Add `Context._package_cache` member, `Context._get_package()` function
- Add `BaseModule.package` member and parameter to constructor
- Add `BaseLoader.load(package)` parameter
- Add `NoSuchBindingError` class
- Add `RequireUnpackSyntaxExtension` class and `require-unpack-syntax` binding
- Add `RequireImportSyntaxExtension` class and `require-import-syntax` binding
- Add `nodepy.python_impl` member
- Add `Context(isolated=True)` parameter
- Add `Context.init` member (an instance of `InitModule`)

__nppm__ *(PPYM post v0.0.17)*

- merged code into Node.py repository (now developed and released alongside
  Node.py)
- renamed to **nppm**
- Fix #9 (partially): Pip install fails with FileNotFoundError: installed-files.txt
  -- added `lib/brewfix.py` which temporarily (over)writes `~/.pydistutils.cfg`,
  only fixes `--user` installs of Node.py (and installs in Virtualenv still
  work flawlessly, too)
- Fix `ppym install --save` saving version as `^VERSION` which is wrong,
  now uses `~VERSION`
- Fix `env:get_module_dist_info()` replacing hyphens by underscores, as Pip
  does it
- Better detection of module `.dist-info`
- To detect the install locations for Node.py modules and scripts, PPYM now
  uses `pip.locations.distutils_scheme()`
- Import `distlib` from `pip._vendor` if it can't be imported as is
- Add `-v,--verbose` option to `ppym install`
- Installing Python dependencies with `--root` and `-g,--global` should now
  be consistent with Pip's default behaviour with the respective installation
  modes (`pip install` and `pip install --user`)
- Configuration option `prefix` is no longer used, (root/global) Node.py
  modules are now installed nearby Python's `site-packages` and Scripts
  are placed into Python's script directory
- Development has been merged into the Node.py repository itself
- `run` command now executes `!` scripts with `$SHELL` completely unprocessed
- `pre-script` no longer recieves the arguments of the script that is being invoked
- Add questions for `"main"` and the `require-unpack-syntax` and
  `require-import-syntax` extensions `nppm init`
- Add `--save-ext` option to `nppm install` command

### v0.0.19

- deprecate `node.py` program name for `nodepy`
- on develop installs, use `node.py-X.Y` name for `setup()` where `X.Y` is the
  Python major and minor version number, to avoid conflicts when installing to
  multiple installations
- add `Require.PY2` and `Require.PY3`
- add `require.symbols(request, symbols=None)` to selectively import symbols
  from another module
- fix `-c` argument
- when a `nodepy_modules/` directory is close to a Node.py module, not only
  Node.py dependencies will be searched in this directory also Python modules
  can be found in it as well (from the `.pip` directory). Note that unlike for
  Node.py modules, the farthest `nodepy_modules/.pip` directory takes precedence
  when importing a Python module and that they are not unique for the scope
  of that module's nearest `nodepy_modules/` directory, and instead will be
  available globally even after the Node.py modules was loaded.
- add `nodepy.proc_args` and `nodepy.executable` data members
- add `require.subprocess()` function
- add `require.subprocess_args()` function
- Fix #20: py_compile causes PermissionError when file is read from an
  unwritable location
- add `-L,--loader` argument to `nodepy` command-line
- add `require(loader=None)` argument
- `nodepy` interactive banner now shows the Python maxsize (usually 32 or 64)
- add `BaseModule.remove()` method
- fix #19: A module that fails to execute must be automatically cleared from
  the module cache again
- upgrade to PPYM v0.0.17

### v0.0.18

- Hotfix for bundled PPYM (now in version v0.0.16) &ndash; fixes installation
  into Python root directory

### v0.0.17

- rename `InteractiveSessionModule` to `InitModule`
- add `-P,--preload` option
- add `nodepy.get_python_library_path()`
- add `doraise=True` to `py_compile.compile()` call
- add `--pymain` option
- Fix #21: Bug with Click and Py2: invalid arguments used for argument parsing
  &ndash; by importing `click` before altering `sys.argv` if possible
- add `require(into)` parameter
- upgrade to PPYM v0.0.15

### v0.0.16

- fix `require('.')` and `require('..')` being resolved in the PATH rather
  then relative to the current directory
- add `BaseModule.parent` and `BaseModule.request`
- add `Context.event_handlers` and `Context.send_event()`
- events `load`, `require` and `enter` are now sent via `Context.event_handlers`
- add `Require.cache`
- add `'__init__'` to `Context.index_files`, `'index'` might get deprecated
  in the future

### v0.0.15

- fix interactive Node.py session (NameError variable `code`)
- now install multiple versions of the `node.py` command for the Python
  version, eg. `node.py3` and `node.py3.5` for Python 3.5
- fix #17: Requiring another package from a develop install does not resolve
  in the original installation directory
- add `Context.resolve(followed_from)` and `Context.load_module(followed_from)`
- add `Context.resolve_and_load()` which automatically adds an element to
  `Require.path` for package links
- add `Require.path`
- add `BaseModule.require`
- remove `UnknownModuleTypeError` for now, `Context.load_module()` now raises
  a `ValueError` if no loader could be determined
- add `Context(bare=False)` parameter
- rename `NodepyModule` to `PythonModule`
- remove `NodepyByteModule`
- add `PythonModule(code)` parameter
- add `get_python_library_base()`
- replace `_py_loader()` function with `PythonLoader` class
- the `PythonLoader` class now writes a bytecache from the source file if
  `PYTHONDONTWRITEBYTECODE` is not set

### v0.0.14

- add nice string representation of `ResolveError`
- Python modules loaded with `require()` no longer inherit Node.py's future flags
- upgrade PPYM to v0.0.13

### v0.0.13

- `setup.py` installs PPYM into user directory if Node.py is installed
  into user directory
- add `--keep-arg0` argument to `node.py`, which is used when PPYM installs
  a command-line script
- `Context.load_module()` now accepts an explicit `loader` argument
- add `Context.get_extension()`
- add `Context.current_modules`
- always add local `nodepy_modules/` directory to `Context.path`
- add `Require.hide_main()`
- `exports` argument to `Require.__call__()`
- add `Context.register_index_file()`

### v0.0.12

- remove `nodepy.Directories` class again, we only need to compute the
  local `nodepy_modules/.pip` library directory
- entering `Context` no longer adds to `PATH`
- upgrade bundled PPYM to v0.0.10
- `setup.py` no longer installs PPYM dependencies
- 12a: Re-add `install_deps()` to `setup.py`, we need to make sure our
  dependencies are installed before PPYM can be bootstrapped

### v0.0.11

- add `Require.__call__(current_dir=None, is_main=False, cache=True)` arguments\
- add `Require.exec_module()` method
- add `Session.load_module(cache=True)` argument
- add `Directories` class which generates the paths to look for Python modules
  installed via Pip through PPYM and more
- entering the Node.py `Context` now adds the local `nodepy_modules/.bin`
  directory to the `PATH` environment variable

### v0.0.10

- extensions are now checked in the order they are registered
- support loading bytecache files with the suffix `.cpython-XY.pyc`
- the `.py` loader now loads the respective bytecache file if appropriate
- `Context.register_binding()` now accepts arbitrary objects, not just
  `BaseModule` instances
- add `require.current` and `Context.current_module` properties
- support for `.nodepy-link` files as created by `ppym install -e`
- add `-v, --verbose` argument for debug prints when resolving module filenames
- use `argparse` instead of `click` due to problem with known arguments
  being consumed and not passed to the Node.py main module
- upgrade bundled PPYM to v0.0.8
- `setup.py develop` now passes `--develop` to `ppym/bootstrap`

### v0.0.9

- `setup.py` -- Fix creation of `node.py` script on Windows by hooking
  `distlib.scripts.ScriptMaker` (see issue #11)
- `require.main` property can now be set
- update bundled PPYM to v0.0.7
- `setup.py` now always upgrades to the bundled PPYM installation
