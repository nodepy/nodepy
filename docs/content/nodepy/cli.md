+++
title = "Commandline"
+++

    $ nodepy --help
    usage: nodepy [-h] [-d] [-c EXPR] [--current-dir DIR] [--version]
                  [--keep-arg0] [-P PRELOAD] [-L LOADER] [--pymain]
                  [--profile PROFILE] [--isolated]
                  ...

    Node.py is a layer on top of the Python runtime which allows to load other
    modules the Node.js way, using a require() function.

    synopsis:
      nodepy                (interactive console)
      nodepy -c EXPR [...]  (evaluate EXPR)
      nodepy REQUEST [...]  (resolve REQUEST and execute it)

    positional arguments:
      arguments

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           Enter the interactive debugger when an exception
                            would cause the application to exit.
      -c EXPR, --exec EXPR  Evaluate a Python expression.
      --current-dir DIR     Change where the initial request will be resolved in.
      --version             Print the Node.py version and exit.
      --keep-arg0           Do not overwrite sys.argv[0] when executing a file.
      -P PRELOAD, --preload PRELOAD
      -L LOADER, --loader LOADER
                            The loader that will be used to load and execute
                            the module. This must be a filename that matches a
                            loader in the Context. Usually the file suffix is
                            sufficient (depending on the loader).
      --pymain
      --profile PROFILE     Profile the execution and save the stats to the specified file.
      --isolated            Create the runtime context in isolated mode.
