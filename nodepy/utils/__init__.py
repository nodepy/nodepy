
try:
  import pathlib
except ImportError:
  import pathlib2 as pathlib


from . import compat, context, iter, machinery, path
from .nopath import PureNoPath, NoPath
from .urlpath import PureUrlPath, UrlPath
