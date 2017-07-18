+++
title = "Config"
+++

NPPM can be configured to use default values for `nppm init` and to remember
your login credentials for one or more package registries. You can also
configure additional registries beyond the default registry, or completely
agument the default registry.

The configuration file is read from `~/.nppmrc` if not otherwise specified
by the `NPPM_CONFIG` environment variable.

By default, this is the configuration that will be used as a fallback when
nothing is configured or the configuration value is not overwritten:

```
author = <current username>
license = MIT

[registry:default]
url = https://registry.nodepy.org
```

You can add additional registries by adding an additional section. The order
in which the sections appear determines the order in which they are resolved.
If the `default` registry is not explicitly specified in the configuration
file, it will always be checked first.

```
[registry:local]
url = http://localhsot:8000
username = CrazyJohn
password = CrazyJohn'sPassword
```
