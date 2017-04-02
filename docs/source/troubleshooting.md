# Troubleshooting

### distutils.errors.DistutilsOptionError: must supply either home or prefix/exec-prefix -- not both

This is a known bug with Pip 9.0.1 when using Homebrew on macOS. Currently, the
only workaround is to install Node.py into a virtual environment.

See [this](http://stackoverflow.com/q/24257803/791713) StackOverflow question.
