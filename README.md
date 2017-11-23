<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
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

Nodepy-pm, Node.py's package manager, allows you to install and manage
standard Python packages (using Pip under the hood) *as well* as Node.py
package. Nodepy-pm is a powerful tool for deploying Node.py applications and
command-line tools.

## Installation

Node.py is available from PyPI as `nodepy-runtime`. The Python version that
you install it into will also be the Python version that you will use in your
Node.py code. (Note that the `six` module is always available when using
Node.py, allowing you to write cross-Python version code easily).

    $ pip install nodepy-runtime

Add the `--user` flag if you don't want to install Node.py system-wide.

## Installing nodepy-pm

Either **install from the online script** using the following command:

    $ nodepy https://nodepy.org/install-pm.py

Or **install from the repository**:

    $ git clone https://github.com/nodepy/nodepy-pm.git
    $ nodepy nodepy-pm/scripts/install.py

**Note** The installer is *not* able to automatically detect whether Node.py
was installed system-wide or with the `--user` option. If you installed Node.py
with the `--user` option, pass the `--global` option to the install-script
(global meaning user-location). The default is to install with `--root`
(system-wide).

    $ nodepy https://nodepy.org/install-pm.py --global

## Todolist

* Python bytecache loading/writing
* Node.js-style traceback (Python's traceback sucks)
