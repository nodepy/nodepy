# Changelog

### v0.0.20

__nodepy__

- Fix `nodepy.proc_args` to contain `sys.executable` if the nodepy executable
  is not an `.exe` on Windows
- Fix #36: pkg_resources DistributionNotFound for packages installed with nodepy-pm
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
  to the extensions listed in a `package.json`

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
- Add `RequireUnpackSyntaxExtension` class

__@nodepy/pm__ *(PPYM post v0.0.17)*

- merged code into Node.py repository (now developed and released alongside
  Node.py)
- renamed to **nodepy-pm**
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
