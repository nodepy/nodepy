# Built-ins

## `require`

Every module has it's own copy of the `require()` function, which is actually
an instance of the `nodepy.context.Require` class. The `require()` function
takes the following arguments:

* request (str) &ndash; A string that can be used to find another module.
  That module will be loaded and it's namespace or exported member
  (`Module.exports`) will be returned.
* exports (bool) &ndash; `True` by default. If this argument is `False`, the
  actual `nodepy.base.Module` object will be returned instead of its namespace
  or exported member.

## `require.main`

The module that is executed via the command-line as the main module. This
module is supposed to behave as being invoked as a program. Modules that
support execution as a program are supposed to check if they are the chosen
module:

```python
if require.main == module:
  main()
```

## `require.breakpoint(tb=None)`

This function starts the interactive debugger. By default, this is Python's
standard debugger `pdb`. The debugger that is invoked can be changed by
changing the `Context.breakpoint` member or setting the `NODEPY_BREAKPOINT`
environment variable. 

If `NODEPY_BREAKPOINT=0`, the breakpoint will be ignored and the function
returns `None` immediately. If it is `NODEPY_BREAKPOINT=` it will be treated
as if it was unset and `Context.breakpoint` will be called. Otherwise, it is
assumed to be a string that is passed to `Context.require()` and the
`breakpoint()` function will be called on the resulting module.

If the *tb* parameter is specified, it must be either `True`, in which case
the traceback is retrieved with `sys.exc_info()[2]`, or otherwise must be a
traceback object. The default implemenetation will then start PDB as a
post-mortem debugger for the traceback.

> See also: [PEP 553](https://www.python.org/dev/peps/pep-0553/)

## `require.starttracing(tracer=None, daemon=True, options=None)`

Start a tracer thread that allows you to inspect the Python stack frames.
By default, it will start an HTTP server listening on `localhost:8081`
which serves an HTML file with all stack frames.

The *tracer* parameter can be `'http'` (default) or `'file'`, or a tracer
object (inheriting from `nodepy.utils.tracing.BaseThread`). The *options*
argument can be used to pass options to the tracer.

If *tracer* is any other string, it will be treated as a requeste and is
`require()`-ed using the `Context.require()` function. The loaded module
must provide a `starttracing(daemon, options)` function that creates,
starts and returns a tracer.

If *tracer* is `None`, it defaults to the value of the `NODEPY_TRACING`
environment variable.

## `require.stoptracing()`

Stops the current tracer, if there is any. The tracer is stored in
`Context.tracer`.

## `module`

The `nodepy.base.Module` object for this file. The `module.namespace` object
is the Python module object in which the file is executed.

```python
assert globals() is vars(module.namespace)
```

## `module.filename`, `module.directory`

A `pathlib2.Path` instance that resembles the filename or directory of the
module, respectively. A module could be loaded not directly from the
filesystem but instead, for example, an internet resource or ZIP file. You
should load resources not using the Python `open()` function or the `os`
module, but instead by starting from the `module.directory` Path object.
