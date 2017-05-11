# upload

```
ppym upload [-f, --force] [-u, --user] [-p, --password] FILENAME
```

For the current version that is specified in the `package.json` of your
project, uploads the specified FILENAME to the package registry. If the
version and/or package does not exist at the time of the upload, the file
will be rejected unless you upload the distribution archive created with
[`ppym dist`](dist) first. If you upload the distribution archive, the
package and package version will be created and assigned to your account.

> __Note__: You should prefer to use the [`ppym publish`](publish) command
> to publish your package as it is less error prone and will also invoke
> the `pre-publish` script if you have one specified in your package manifest.

Read about the [Requirements](publish#requirements) to publish a package.
