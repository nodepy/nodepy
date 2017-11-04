<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
<h1 align="center">Node.py (WIP)</h1>
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img src="https://travis-ci.org/nodepy/nodepy.svg?branch=develop">
</p>
<p align="center">
  A Node.js-like runtime for Python (incl. a
  <a href="https://github.com/nodepy/nodepy-pm">package manager</a>).
</p>

__Installing Node.py__

> Note: This version is currently in development and not yet available
> via Pip. Please install from the Git source repository instead.

```
$ pip install nodepy-runtime
$ nodepy --version
```

__Installing the Node.py Package Manager__

The package manager can be installed by passing the URL to the remote install
script to the `nodepy` command-line. Alternatively, you can clone the
[Node.py PM] source repository and run the install script.

  [Node.py PM]: https://github.com/nodepy/nodepy-pm

```
$ nodepy https://nodepy.org/install-pm
$ ## Alternatively
$ git clone https://github.com/nodepy/nodepy-pm.git
$ nodepy nodepy-pm/scripts/install
```

Check the package manager version and update your `PATH`:

```
$ nodepy-pm version
$ export PATH="$PATH:$(nodepypm bin):$(nodepypm bin -g)"
```

__Running scripts__

```
$ cat >hello.py <<EOL
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('name')

if require.main:
  args = parser.parse_args()
  print('Hello,', args.name)
EOL
$ nodepy ./hello John
Hello, John
```

---

## Todolist

* Python bytecache loading/writing
* Node.js-style traceback (Python's traceback sucks)
