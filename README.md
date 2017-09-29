<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
<h1 align="center">Node.py</h1>
<img align="right" src="https://img.shields.io/badge/License-MIT-yellow.svg">
<p align="center">A Node.js-like runtime for Python (incl. package manager).</p>


```
$ pip install node.py
$ nodepy --version
$ export PATH="$PATH:.nodepy_modules/.bin"
```

__Upgrade nodepy-pm__

```
$ nodepy-pm install --root --upgrade @nodepy/nodepy-pm
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
* Package-link support
* Node.js-style traceback (Python's traceback sucks)
