# require()

The `require()` function in Node.py is available for every module that is
executed through the Node.py command-line or again loaded with the `require()`
function. It is an instance of the `nodepy.Require` class and the instance is
unique in every module.

## API

### `require()`

`require(request, current_dir=None, is_main=False, cache=True,
         exports=True, exec_=True, into=None, symbols=None)`

Resolve *request* into a module filename and load that module. For relative
paths, the *current_dir* will be used to resolve the request (defaults to
the parent directory of the module that owns the #Require instance).

If *is_main* is True, non-relative requests will also be resolved in the
*current_dir* first. Note that the #Context will raise a #RuntimeError when
there is already a #Context.main_module, thus it is recommended to use #exec_main().

If *cache* is False, the request will not be cached and also not be looked
up into the cache.

If *exports* is False, the actual #BaseModule object is returned, otherwise
the #BaseModule.namespace or even #BaseModule.namespace.exports member if
exists.

If *exec_* is False, the module will only be loaded and not be executed.
Note that the module may have already been loaded on another occassion!

If *into* is specified, this function behaves like a Python star-import and
will import all members of the module that would normally be returned into
the specified dictionary. Usually, you'll want to pass `globals()` to this
parameter.

### `require.symbols()`

`require.symbols(request, symbols=None)`

### `require.module`

### `require.main`

### `require.current`

### `require.context`

### `require.path`

### `require.cache`
