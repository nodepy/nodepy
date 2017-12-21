+++
title = "Changelog"
+++

## v2.0.2

* `PythonLoader.load()` no longer adds to `sys.path` if the path already is
  in the list

## v2.0.1

* `PythonLoader._load_code()` now uses utf8 encoding by default, however we
  should try to peek into the file to see if it contains a coding: comment
* always add local `modules_directory` to Context resolve path, this helps
  projects that use package links
* Node.py repl can now also import from `.nodepy/pip` directory
* fix `resolve_root` outside of package root
* don't import `pathlib` from `nodepy.utils.path`, but instead import
  `pathlib2` directly. We decided on not using std `pathlib` if it is
  available, as there can be minor differences
* add missing `strict=False` to `UrlPath.resolve()` and `ZipPath.resolve()`
* add info to `nodepy.runtime.scripts` that it can also holds an `args` member
* `resolve_root` now taken into account for default `Package.main` if it is
  not explicitly defined, add `resolve_root` when package entry point is required
* `StdResolver.package_for_directory()` must resolve the path to eliminate
  pardir elements, otherwise we can end up with two Packages pointing to the
  same directory, but one contains `subdir/..` elements
* update `Module.name` property to be able to produce a requirable module name
  for modules outside a package's `resolve_root`
* fixed comparing RequestString with actual request str in `Request.try_()`
  to properly raise TryResolveError
* fix `FrameDebugger` parent calls for Python 2
* add `Config.sections()`, remove debug print in `Context.__init__()`
* remove `nodepy.default_context`, but add `nodepy.get_default_context()` instead
* add `nodepy.utils.config` module and add `Context.config` member which is
  initialized from the `NODEPY_CONFIG` file or `~/.nodepy/config`

## v2.0.0

* Complete rewrite
* Abstract module resolving interface
* Using the `pathlib2` module to abstract the filesystem
