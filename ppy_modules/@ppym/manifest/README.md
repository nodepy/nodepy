# @ppym/manifest

Parse package manifests.

```python
manifest = require('@ppym/manifest')
try:
  m = manifest.parse('package.json')
except (FileNotFoundError, manifest.InvalidPackageManifest) as exc:
  print(exc)
  m = None
```
