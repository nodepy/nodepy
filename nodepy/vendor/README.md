Vendored Python libraries.

* `toml` from v0.9.3
  * add `*args, **kwargs` arguments to `toml.dump()`, forwarding to internally
    used `toml.dump()` call
  * fix quoting of section name when rendering inline table (see uiri/toml#130)
