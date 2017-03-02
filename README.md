<img src="http://i.imgur.com/CdzJiFi.png" align="right" width="150px"></img>
# Node.py

Node.py is a loader for Python modules in the Node.js-style. Unlike standard
Python modules, the Node.py `require()` caches modules by their filename and
thus allows modules with the same name be loaded from multiple locations at
the same time.

The goal of this project is to develop a Python environment that can execute
without module collisions (resulting in one component in the process recieving
the wrong module) and a more sophisticated approach to the module finding and
loading process.

Node.py has its own package ecosystem managed by [ppym] and the
[PPYM package registry].

  [ppym]: https://github.com/ppym/ppym
  [PPYM package registry]: https://github.com/ppym/registry

__Requirements__

- Python 2.6+ or Python 3.3+

__Installation__

    pip install node.py

__Synopsis__

    node.py            (enter interactive session)
    node.py <request>  (resolve request into a filename and run it as a
                        Python script in Node.py environment)

__Todo__

- Alternative script names for `node.py` and `ppym` depending on the Python
  version it is installed into
- Support package links for ppym develop installs
- Support many of Node.js's original command-line arguments
- Testcases for Python 2 and 3
