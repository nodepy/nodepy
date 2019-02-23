# Getting Started


The `nodepy` command-line allows you to use a REPL or run a Python script.
Node.py can load and execute all standard Python scripts, only that such
scripts will then have access to Node.py's additional built-ins, such as the
`require()` function and the specialized `import` syntax.

```python
import {hello} from './hello'   # same as: hello = require('./hello').hello

if require.main == module:
  hello('John')
```

**Note** that in Node.py we test for `require.main == module` instead of
`__name__ == '__main__'`. If you want to run a standard Python script
that tests for `__name__` with Node.py, you need to pass the `--pymain`
argument, like

    $ nodepy --pymain myscript.py
