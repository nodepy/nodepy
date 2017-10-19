"""
Standard extensions usually available to Node.py instances.
"""

from nodepy import base
import re


class ImportSyntax(base.Extension):
  """
  This extension preprocess Python source code to replace a new form of the
  import syntax with valid Python code.

  # Examples

  ```python
  import 'module'             # Just import, no name assigned
  import 'module' as default_member
  import default_member from 'module'
  import {some_member} from 'module'
  import {some_member as new_name} from 'module'
  import {foo, bar, spam, egg} from 'module'
  import * from 'module'
  import default_member, * from 'module'

  # Assign to another member already in the scope.
  import existing_member.foo from 'module'

  # Multiline supported
  import {some_member}
    from 'module'
  ```
  """

  _re_import_as = re.compile(
    r'''^(?P<indent>[^\S\n]*)import\s+(?P<q>"|')(?P<mod>.*?)(?P=q)(?:\s+as\s+(?P<n>[\.\w]+))?[^\S\n]*$''',
    re.M
  )
  _re_import_from = re.compile(
    r'''
    ^(?P<indent>[^\S\n]*)   # Keep track of the indentation level
    import\s+
    (?P<members>
      (?:
        [\.\w]+|            # Default member
        (?:[\.\w]+\s*,\s*)?     # Default member + specific members
      )?
      (?:
        \{[^}]+\}|          # Specific members
        \*                  # Starred-import
      )?
    )\s+
    from\s+
    (?P<q>["'])(?P<mod>.*)(?P=q)[^\S\n]*$
    ''',
    re.M | re.X
  )
  _regexes = [(_re_import_as, 'as'), (_re_import_from, 'from')]

  @staticmethod
  def __import_symbols_from_stmt(module, symbols):
    stmt = '_reqres=require({!r}, exports=False).namespace;'.format(module)
    for name in symbols:
      alias = name = name.strip()
      parts = re.split('\s+', name)
      if len(parts) == 3 and parts[1] == 'as':
        name, __, alias = parts
      stmt += '{0}=_reqres.{1};'.format(alias, name)
    return stmt + 'del _reqres'

  def preprocess_python_source(self, module, source):
    while True:
      for regex, kind in self._regexes:
        match = regex.search(source)
        if match: break
      else:
        break

      if kind == 'as':
        as_name = match.group('n')
        if as_name:
          repl = '{}=require({!r})'.format(as_name, match.group('mod'))
        else:
          repl = 'require({!r})'.format(match.group('mod'))
      elif kind == 'from':
        module = match.group('mod')
        members = match.group('members')
        if members == '*':
          repl = 'require.star({!r})'.format(module)
        elif '{' in members:
          if members.startswith('{'):
            default_name = None
          else:
            default_name, members = members.partition(',')[::2]
            members = members.lstrip()
            assert members.startswith('{')
          assert members.endswith('}')
          repl = self.__import_symbols_from_stmt(module, members[1:-1].split(','))
          if default_name:
            repl = '{}=require({!r});'.format(default_name, module) + repl
        elif members.endswith('*') and members.count(',') == 1:
          default_member = members.split(',')[0].strip()
          repl = 'require.star({0!r}); {1}=require({0!r})'.format(module, default_member)
        else:
          repl = '{}=require({!r})'.format(members, module)
      else:
        raise RuntimeError

      # Add additional newlines to the replacement until it spans
      # the same number of newlines than the matched sequence. This
      # is to keep error message more consistent.
      repl = match.group('indent') + repl + '\n' * match.group(0).count('\n')

      source = source[:match.start()] + repl + source[match.end():]

    return source
