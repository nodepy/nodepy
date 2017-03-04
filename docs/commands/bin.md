# bin

```
ppym bin [--global] [--pip]
```

Prints the local or global binary directory that PPYM installs to. If you
pass the `--pip` switch, the Pip binary directory will be printed instead.

Note that [`ppym install`](install) will automatically create wrappers in
the Node.py binary directory that reference respective commands in the Pip
binary directory, thus if you have Python dependencies that expose scripts,
you only need to add the Node.py binary directory to your path.

The local binary directory is `nodepy_modules/.bin`.
