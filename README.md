<img src="http://i.imgur.com/Q4jjufa.png" align="left"></img>*
# @ppym/engine

PPY is kind of a Node.js clone. This is the PPY engine that lays the foundation
for loading Python modules resolved from actual filenames with a `require()`
function.

Installing the PPY engine with [Pip] will automatically install **ppym**, the
PPY package manager. The engine itself relies on some code that is contained in
new-style Python modules and will bootstrap these modules automatically (see
the `ppy_modules/` directory for a list of the bootstrapped modules that are
also automatically installed with PPY).

  [Pip]: https://pypi.python.org/pypi/pip

__Goal__ 

The goal of this project is to develop a Python environment that can execute
Python code **free from global state**. I have come across problems with the
global interpreter state especially in Python plugin development.

__Synopsis__

    ppy                         (enter interactive session)
    ppy <request>               (resolve request into a filename and run
                                 it as a Python script in the ppy environment)

Requests are resolved similar to the way Node.js does it.

__Example__

```
$ ls
index.py utils.py ppy_modules/
$ cat index.py
```
```python
manifest = require('@ppym/manifest')
utils = require('./utils')
if require.is_main:
  utils.print_manifest_info(manifest.parse('package.json'))
```
```
$ ppy index
Information on manifest of package "demo-app@1.0.0"
- Filename: package.json
- Directory: .
- License: MIT
[...]
```

---

<sub>\* Original image from http://www.rcsinnovations.com/wp-content/uploads/2012/09/Popeye1.gif.
If anyone can find or make a similar image of PopPey with specific information on copyright and
license, that would be great.</sub> 
