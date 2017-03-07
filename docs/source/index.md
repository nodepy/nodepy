<img src="https://i.imgur.com/IfmOKFI.png" align="right" width="150px"></img>

# Node.py v0.0.13 Documentation

Node.py is a loader for Python modules that offers a `require()` function.
Unlike standard Python modules, Node.py modules are cached by their filename,
thus multiple modules with the same name but from different locations can be
loaded without collisions.

## Synopsis

    node.py            (enter interactive session)
    node.py <request>  (resolve request into a filename and run it as a
                        Python script in Node.py environment)
