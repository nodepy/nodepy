Every package can make use of extensions that receive events when modules
for that package are loaded. This is especially useful for hooking up
transpilers during the runtime of the application.

Extensions are specified in the `package.json` manifest under the
`"extensions"` field. Every extension must be requireable from the
location of the `package.json` manifest.

__Example__

```json
{
  "name": "myapp",
  "version": "1.0.0",
  "extensions": [
    "./myextension",
    "!require-import-syntax"
  ]
}
```

## Extension callbacks

Every extension can provide one of the following member functions that will
be invoked on certain events.

### init_extension

    init_extension(package)

Called when the extension is loaded for a package.

### module_loaded

    module_loaded(module)

Called after a module was loaded.

### preprocess_python_source

    preprocess_python_source(package, filename, source)

Called when a Python source file is loaded. Return a modified version of
*source*. This is used by the existing transpilers (see below).


## Built-in extensions

### require-import-syntax

This extension is available as a Context binding which can be required
with `!require-import-syntax`, which is also the string to enter in the
`"extensions"` field. This extension allows you to use a special import
syntax in your Python source files in place of the `require()` function.

```python
# No symbol made available in the current namespace, only for side-effects
# of the module import.
import "module-name"   

# Import the actual module namespace, NOT the default exported member.
import "module-name" as module

# Import the default member from the module namespace.
import default_member from "module-name"

# Import one or more members from the module namespace. Note that line
# breaks are allowed.
import {member1, member2}
  from "module-name"

# Alias a member from a module.
import {
  really_long_member1 as member1,
  member2
} from "module-name"

# Import the default member and also other members from the module.
import default_member, {
  really_long_member1 as member1,
  member2
} from "module-name"
```

### require-unpack-syntax

This extension allows you to use a special syntax to import members
from a required module. The extension is also available as a Context binding.

```python
{ really_long_member1 as member1, member2 } = require('module-name')
```
