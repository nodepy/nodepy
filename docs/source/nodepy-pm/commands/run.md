# run

```
ppym run SCRIPT [ARGS]
```

Runs the SCRIPT that is specified in the current package's manifest. Note that
some scripts have special meanings and will be invoked automatically by other
procedures of PPYM.

## Example

```json
{
  "scripts": {
    "build-docs": "!mkdocs build",
    "pre-publish": "scripts/pre-publish.py"
  }
}
```

    $ ppym run build-docs
