# publish

```
ppym publish [-f,--force] [-u,--user] [-p,--password]
```

A combination of [`ppym dist`](dist) and [`ppym upload`](upload) that also
invokes the `pre-publish` and `post-publish` [scripts](run).

## Requirements

In order to publish a package to [ppym.org](https://ppym.org), it must
meet the following requirements:

- The `name` of the package must be scoped with your username (ie. `@username/packagename`)
- The `license` field in `package.json` must not be empty

After a package version has been uploaded to the registry, arbitrary files
may be uploaded to that version as well. This is intended to be used for
additional files that may be downloaded by the actual package when necessary.
Note that https://ppym.org currently has a size upload limit of 2MiB.

It is important that you read and understand the [PPYM Registry Terms of Use][0]
before you publish packages and upload content to the registry.

  [0]: https://ppym.org/terms
