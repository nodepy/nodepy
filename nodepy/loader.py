"""
Implements the #resolver.StdResolverLoader interface for Python modules.
"""

from nodepy import base, resolver, utils


class PythonModule(base.Module):

  def load(self):
    self.init()
    self.loaded = True
    with self.filename.open('r') as fp:
      code = fp.read()

    extensions = utils.iter.Chain(self.context.extensions)
    if self.package:
      require = self.package.require
      extensions << (require(ext) for ext in self.package.extensions)

    for ext_module in extensions:
      if hasattr(ext_module, 'init_extension'):
        ext_module.init_extension(self.package, self)
      if hasattr(ext_module, 'preprocess_python_source'):
        code = ext_module.preprocess_python_source(self, code)

    code = compile(code, str(self.filename), 'exec', dont_inherit=True)
    exec(code, vars(self.namespace))


class PythonLoader(resolver.StdResolver.Loader):

  def suggest_files(self, path):
    return [path.with_suffix('.py')]

  def can_load(self, path):
    return path.suffix == '.py'

  def load_module(self, context, package, filename):
    return PythonModule(context, package, filename)
