Python code that is invoked via **nodepy** has a few additional built-ins
available.

- `require()`
- `module`
- `__directory__`

## `require()`

```
require(request, current_dir=None, is_main=False, cache=True,
        exports=True, exec_=True, into=None, symbols=None)
```

The `require()` function in **nodepy** is available to every module that is
executed through the nodepy command-line or which is in turn loaded with the
`require()` function. It is an instance of the `nodepy.Require` class,
created uniquely for every loaded module.

A special syntax loading only some components of a module is supported, which
is called the "require unpack" syntax. It is turned into valid Python code
before a module is loaded. Instead of having to assign the required module to
a temporary variable or using the require function multiple times

```python
member_1 = require('some-module').member_1
member_2 = require('some-module').this_is_called_differently
```

you can use the "require unpack" syntax.

```python
{ member_1, this_is_called_differently as member_2 } = require('some-module')
```

## `require.context`

The `nodepy.Context` object that is currently in charge of the execution.

## `require.main`

Alias for `require.context.main_module`. Returns the main `nodepy.BaseModule`
object that is being executed. Note that the main module can change during
execution of a program by using `require.exec_main()`.

## `require.current`

The currently executed `nodepy.BaseModule`. A module is on the stack of
currently executed modules until the execution has reached the end of the
script and the `require()` function that was used to load it returns.

## `require.exec_main()`

Execute another module as the new main module. As soon as `exec_main()`
returns, the original main module will be in place again.

## `require.path`

Nodepy module search path for this `nodepy.Require` instance.

## `module`

This built-in is the `nodepy.BaseModule` object that represents the module
that is being executed. This is commonly used to check if the module is
executed as the main module.

```python
if require.main == module:
  # ...
```

## `__directory__`

Contains the parent directory of the currently executed module. This is the
same as `os.path.dirname(__file__)` and is provided for convenience.
