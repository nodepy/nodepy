# nnp

**nnp** is a runner for Python modules, and **nnpm** is its package manager.
The key concept is derived from *Node.js* and *npm*, though originally *Pyn*
was intended as part of *[Craftr]*.

  [Craftr]: https://craftr.net

## Synopsis

    [x] nnp
    [x] nnp <script>.py
    [x] nnp -p <package>[@<version>][/<module>][:<func>]
    [/] nnpm install [-g] .
    [/] nnpm install [-g] <package>[@<version>]
    [ ] nnpm uninstall [-g] <package>[@<version>]
    [ ] nnpm init
    [ ] nnpm ls
    [ ] nnpm register
    [ ] nnpm dist [<type>]
    [ ] nnpm upload <archive>

## Packages

**nnpm** can install packages locally into the `nnp_packages/` directory or
globally into `~/.nnp/packages` from a remote registry or from an existing
package directory. Similar to *Node.js*, packages in Pyn require a manifest.

When a package is ready to be made publicly available, it can be uploaded to
the package registry. First it needs to be regsitered, then a distributable
package archive must be created, which can be then be uploaded.

Example manifest:

```json
{
  "name": "demo-app",
  "version": "1.0.0",
  "main": "index.py",
  "engines": {
    "python": ">=3.0.0"
  },
  "bin": {
    "demo-app": "index.py"
  },
  "scripts": {
    "say-hello": "echo \"Hello!\""
  },
  "dependencies": {
    "exile": "~1.2.0"
  },
  "python-dependencies": {
    "requests": "==2.13.0",
    "glob2": "==0.4.1"
  },
  "dist": {
    "include_files": ["README.md", "*.py", "public/*"]
  }
}
```
