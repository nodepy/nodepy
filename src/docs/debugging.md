# Debugging

For program tracing, please check the `require.breakpoint()` documentation.
If your application terminates due to an exception, you can either pass the
`--pmd` flag to the Node.py command-line or set the `NODEPY_PMD` environment
variable. This will automatically enter the post-mortem debugger on exceptions
that propagate all the way up to `sys.excepthook()`.

    $ NODEPY_PMD=x nodepy ./index.py

**Important:** If the value of `NODEPY_PMD` is an integer, it will be
decremented for the continuation of the process. If the value reaches zero,
the variable will be unset. This gives you some flexibility when debugging
applications that spawn other Node.py child processes.
