### must supply either home or prefix/exec-prefix -- not both

```
distutils.errors.DistutilsOptionError: must supply either home or prefix/exec-prefix -- not both
```

Before **nppm** v0.0.20, this error could appear on macOS and Python
versions installed via [Homebrew] (see [this StackOverflow question][0]).
Since this version, the package manager creates or temporarily overwrites
the file `~/.pydistutils.cfg` to set an empty `prefix`.

If you still encounter this error, please [create an issue][new issue].

  [0]: http://stackoverflow.com/q/24257803/791713
  [Homebrew]: https://brew.sh
  [new issue]: https://github.com/nodepy/nodepy/issues/new

### No such file or directory: '.../installed-files.txt'

```
FileNotFoundError: [Errno 2] No such file or directory: 'nodepy_modules.pip\\Lib\\site-packages\\aniso8601-1.2.1-py3.5.egg-info\\installed-files.txt'
```

*This appears to be an issue with Pip that appears when installing some modules
when using the `pip install --prefix` option. Using `pip install --target` can
fix the problem when you experience it. You can use `--pip-use-target-option`
for `nppm install` take make it use the `--target` option instead.*

This bug will be/is fixed in Pip 9.0.2, so upgrade if you can.
