
from nodepy.extensions import call_function_get_frame


def test_call_function_get_frame():
  def test():
    value = 42
  frame = call_function_get_frame(test)[0]
  try:
    assert frame.f_locals['value'] == 42
  finally:
    del frame
