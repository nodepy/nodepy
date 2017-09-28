"""
Implements the #resolver.StdResolverLoader interface for Python modules.
"""

from nodepy import base, resolver


class PythonModule(base.Module):

  def load(self):
    self.init()
    self.loaded = True
    with self.filename.open('r') as fp:
      code = compile(fp.read(), str(self.filename), 'exec', dont_inherit=True)
    exec(code, vars(self.namespace))


class PythonLoader(resolver.StdResolver.Loader):

  def suggest_files(self, path):
    return [path.with_suffix('.py')]

  def can_load(self, path):
    return path.suffix == '.py'

  def load_module(self, context, package, filename):
    return PythonModule(context, package, filename)
