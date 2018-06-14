<p align="center"><img src="https://i.imgur.com/fy4KZIW.png" height="128px"></p>
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img src="https://travis-ci.org/nodepy/nodepy.svg?branch=develop">
</p>
<h2>Node.py</h2>

Node.py is a Python runtime compatible with CPython 2.7 and 3.3 &ndash; 3.6.
It provides a separate but superior import mechanism for modules, bringing
dependency management and ease of deployment for Python applications up to par
with other languages, **without virtualenvs**. Node.py is inspired by
[Node.js](https://nodejs.org).

**nppm** is Node.py's package manager that allows you to install and manage
standard Python packages (using Pip under the hood) *as well* as Node.py
packages without the hazzle of virtual environments. **nppm** is a powerful
tool for deploying Node.py applications and command-line tools.

## Installation

Node.py is available from PyPI as `nodepy-runtime`. The Python version that
you install it into will also be the Python version that you will use in your
Node.py code.

> Tipp: Add the `--user` flag if you don't want to install Node.py system-wide.

    $ pip install nodepy-runtime

There are multiple ways of installing **nppm**. The suggested method is to
use the remote install script. If you want to install a specific version,
pass the Git ref as an argument (eg. `develop` or `v2.0.2`). If you don't
specify a tag, the highest tagged version will be installed.

    $ nodepy https://nodepy.org/install-pm.py

Alternatively, you can clone the repository and use the local install script.

    $ git clone https://github.com/nodepy/nppm.git
    $ nodepy nppm/scripts/install.py

> Important: The installer is **not** able to automatically detect whether
> Node.py was installed system-wide or with the `--user` option. If you
> installed Node.py with the `--user` option, pass the `--global` option to
> the install-script (global meaning user-location). The default is to install
> with `--root` (system-wide).

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
