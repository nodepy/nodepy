<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# Node.py v0.0.19 Documentation

```
usage: nodepy [-h] [-d] [-v] [-c EXPR] [--current-dir DIR] [--version]
              [--keep-arg0] [-P PRELOAD] [--pymain]
              ...
```

Node.py is a layer on top of the Python runtime which allows to load other
modules the Node.js way, using a [require()][require] function. It has it's own
[package ecosystem][ppym.org] and [package manager][PPYM]. Of course, standard
Python modules can still be used and are explicitly supported by [PPYM][] and
the [package manifest][].

  [require]: require
  [ppym]: https://github.com/nodepy/ppym
  [ppym.org]: https://ppym.org
  [package manifest]: ppym/package-manifest

__Synopsis__

    nodepy                (interactive console)
    nodepy -c EXPR [...]  (evaluate EXPR)
    nodepy REQUEST [...]  (resolve REQUEST and execute it)

__Positional Arguments__

    arguments

__Optional Arguments__

    -h, --help            show this help message and exit
    -d, --debug           Enter the interactive debugger when an exception would cause the application to exit.
    -v, --verbose         Be verbose about what's happening in the Node.py context.
    -c EXPR, --exec EXPR  Evaluate a Python expression.
    --current-dir DIR     Change where the initial request will be resolved in.
    --version             Print the Node.py version and exit.
    --keep-arg0           Do not overwrite sys.argv[0] when executing a file.
    -P PRELOAD, --preload PRELOAD
    --pymain
