<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
<h1 align="center">Node.py</h1>
<img align="right" src="https://img.shields.io/badge/License-MIT-yellow.svg">
<p align="center">
  A Node.js-like runtime for Python (incl. a
  <a href="https://github.com/nodepy/nodepy-pm">package manager</a>).
</p>

__Installing Node.py__

```
$ pip install node.py
$ nodepy --version
```

__Installing Node.py PM__ (and relevant paths)

  [Node.py PM]: https://github.com/nodepy/nodepy

```
$ nodepy https://nodepy.org/install-pm
$ nodepy-pm version
$ export PATH="$PATH:$(nodepy-pm bin):$(nodepy-pm bin -g)"
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
