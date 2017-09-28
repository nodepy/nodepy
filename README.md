<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
<h1 align="center">Node.py</h1>
<p align="center">A Python runtime which offers a module-solution similar to Node.js.</p>


```python
this = require('that')
pathutils = require('./utils/path')

if require.main == module:
  print('Hello, World!')
```

---

This is a re-implementation of Node.py 0.0.22 and will be released as
version 0.1.0.

__Todo__

* Python bytecache loading/writing
* Package-link support
* Node.js-style traceback (Python's traceback sucks)
* Use `localimport` and allow loading of Python modules from `.nodepy_modules/.pip`
