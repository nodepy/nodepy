# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import collections


def tn(value):
  return type(value).__name__


def validate(name, value, schema):
  """
  A helper function to validate function parameters type and value.
  The *schema* must be a dictionary and supports the following keys:

  - ``type``: A single type or a list of accepted types
  - ``bool_validators``: A function or a list of functions that return
    True if the *value* is valid, False otherwise.
  - ``validators``: A function or a list of functions that raise a
    :class:`ValueError` if the *value* is invalid.
  - ``items``: If *value* is a sequence, this key must provide a sub-schema
    that holds true for all of the items in the sequence. Note that it will
    not be applied to iterables.
  - ``allowEmpty``: If specified, must be True or False. If True, allows
    *value* to be an empty sequence, otherwise not.
  """

  schema.setdefault('type', [])
  schema.setdefault('bool_validators', [])
  schema.setdefault('validators', [])

  if isinstance(schema['type'], list):
    schema['type'] = tuple(schema['type'])
  elif not isinstance(schema['type'], tuple):
    schema['type'] = (schema['type'],)
  schema['type'] = tuple(type(None) if x is None else x for x in schema['type'])

  if schema['type'] and not isinstance(value, schema['type']):
    raise TypeError("argument '{}' expected one of {} but got {}".format(
      name, '{'+','.join(x.__name__ for x in schema['type'])+'}', tn(value)))
  if isinstance(value, collections.Sequence):
    if 'items' in schema:
      for index, item in enumerate(value):
        validate('{}[{}]'.format(name, index), item, schema['items'])
    if not schema.get('allowEmpty', True) and not value:
      raise ValueError("argument '{}' can not be empty".format(name))

  if not isinstance(schema['bool_validators'], (list, tuple)):
    schema['bool_validators'] = [schema['bool_validators']]
  for validator in schema['bool_validators']:
    if not validator(value):
      raise TypeError("argument '{}' is not {}".format(name, validator.__name__))

  if not isinstance(schema['validators'], (list, tuple)):
    schema['validators'] = [schema['validators']]
  for validator in schema['validators']:
    validator(value)
