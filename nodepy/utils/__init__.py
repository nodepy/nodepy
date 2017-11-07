
import pathlib2 as pathlib
import pdb
import six
import sys

from . import context, iter, machinery, path


def as_text(x, encoding=None):
  """
  Accepts a binary or unicode string and returns a unicode string. If *x* is
  not a string type, a #TypeError is raised.
  """

  if not isinstance(x, six.string_types):
    raise TypeError('expected string, got {} instead'.format(type(x).__name__))
  if not isinstance(x, six.text_type):
    x = x.decode(encoding or sys.getdefaultencoding())
  return x


class FrameDebugger(pdb.Pdb):
  """
  This debugger allows to interact with a frame after it has completed
  executing, much like #pdb.post_mortem() but without requiring a traceback.
  """

  def interaction(self, frame, traceback=None):
    """
    Allows you to interact with the specified *frame*. If a *traceback* is
    specified, the function behaves just like #pdb.Pdb.interaction(). Use
    this function for dead frames only. If you want step-by-step debugging,
    use the #set_trace() method instead.
    """

    # This is just a proxy function for documentation purposes.
    self.reset()
    return super(FrameDebugger, self).interaction(frame, traceback)

  def setup(self, f, tb):
    if tb is not None:
      return super(FrameDebugger, self).setup(f, tb)
    else:
      # Imitate what the parent function is doing as much as possible,
      # but without a traceback
      self.forget()
      self.stack, self.curindex = self.get_stack(f, tb)
      # XXX We may still need to reproduce the following lines:
      """
      while tb:
        # when setting up post-mortem debugging with a traceback, save all
        # the original line numbers to be displayed along the current line
        # numbers (which can be different, e.g. due to finally clauses)
        lineno = lasti2lineno(tb.tb_frame.f_code, tb.tb_lasti)
        self.tb_lineno[tb.tb_frame] = lineno
        tb = tb.tb_next
      """
      self.curframe = self.stack[self.curindex][0]
      # The f_locals dictionary is updated from the actual frame
      # locals whenever the .f_locals accessor is called, so we
      # cache it here to ensure that modifications are not overwritten.
      self.curframe_locals = self.curframe.f_locals
      return self.execRcLines()
