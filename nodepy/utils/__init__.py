
try:
  import pathlib
except ImportError:
  import pathlib2 as pathlib


from . import compat, context, iter, machinery, path
from .urlpath import PureUrlPath, UrlPath
