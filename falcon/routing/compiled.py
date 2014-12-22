# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re


class CompiledRouter(object):
    """Fast URI router which compiles it's routing logic to Python code.

    This class is a Falcon router, which handles the routing from URI paths
    to resource class instance methods. It implements the necessary router
    methods add_route() and find(). Generally you do not need to use this
    router class directly, as an instance is created by default when the
    falcon.API class is initialized.

    The router treats URI paths as a tree of URI segments and searches by
    comparing a URI one segment at a time. Instead of interpreting the route
    tree for each look-up, it generates inlined, bespoke Python code to
    perform the search and compiles it, making it blazingly fast.

    The generated code for the test() method looks something like this:

    def test(path, return_values, expressions, params):
      path_len = len(path)
      if path_len > 0 and path[0] == "books":
        if path_len > 1:
          params["book_id"] = path[1]
          return return_values[1]
        return return_values[0]
      if path_len > 0 and path[0] == "authors"
        if path_len > 1:
          params["author_id"] = path[1]
          if path_len > 2:
            match = expressions[0].search(path[2])
            if match is not None:
              params.update(match.groupdict())
              return return_values[4]
          return return_values[3]
        return return_values[2]
    """

    def __init__(self):
        self._roots = []
        self._find = None
        self._code_lines = None
        self._expressions = None
        self._return_values = None

    def add_route(self, uri_template, method_map, resource):
        """Adds a route between URI path template and resource."""
        path = uri_template.strip('/').split('/')

        # Reset compiled code
        self._find = None

        def insert(nodes, path_index=0):
            for node in nodes:
                if node.matches(path[path_index]):
                    path_index += 1
                    if path_index == len(path):
                        node.method_map = method_map
                        node.resource = resource
                    else:
                        insert(node.children, path_index)

                    return

            # NOTE(richardolsson): If we got this far, the node doesn't already
            # exist and needs to be created. This builds a new branch of the
            # routing tree recursively until it reaches the new node leaf.
            new_node = CompiledRouterNode(path[path_index])
            nodes.append(new_node)
            if path_index == len(path) - 1:
                new_node.method_map = method_map
                new_node.resource = resource
            else:
                insert(new_node.children, path_index + 1)

        insert(self._roots)

    def find(self, uri):
        """Finds resource and method map for a URI, or returns None."""
        if self._find is None:
            self._compile()

        path = uri.lstrip('/').split('/')
        params = {}
        node = self._find(path, self._return_values, self._expressions, params)

        if node is not None:
            return node.resource, node.method_map, params
        else:
            return None, None, None

    def _compile_node(self, node=None, pad='  ', level=0):
        """Generates Python code for a router node (and it's children)."""
        def line(pad, lstr):
            self._code_lines.append(pad + lstr)

        if node.is_var:
            line(pad, 'if path_len > %d:' % level)
            if node.is_complex:
                # NOTE(richardolsson): Complex nodes are nodes which contain
                # anything more than a single literal or variable, and they
                # need to be checked using a pre-compiled regular expression.
                expression_idx = len(self._expressions)
                self._expressions.append(node.var_regex)
                line(pad, '  match = expressions[%d].search(path[%d]) # %s' % (
                    expression_idx, level, node.var_regex.pattern))

                line(pad, '  if match is not None:')
                line(pad, '    params.update(match.groupdict())')
                pad += '  '
            else:
                line(pad, '  params["%s"] = path[%d]' % (node.var_name, level))
        else:
            line(pad, 'if path_len > %d and path[%d] == "%s":' % (
                level, level, node.raw_segment))

        if node.resource is not None:
            resource_idx = len(self._return_values)
            self._return_values.append(node)

        if len(node.children):
            for child in node.children:
                self._compile_node(child, pad + '  ', level + 1)
        if node.resource is not None:
            line(pad, '  return return_values[%d]' % resource_idx)

    def _compile(self):
        """Generates Python code for entire routing tree.

        The generated code is compiled and the resulting Python method is
        stored in the _find member.
        """
        self._return_values = []
        self._expressions = []
        self._code_lines = [
            'def find(path, return_values, expressions, params):',
            '  path_len = len(path)',
        ]

        for root in self._roots:
            self._compile_node(root)

        src = '\n'.join(self._code_lines)

        scope = {}
        exec(compile(src, '<string>', 'exec'), scope)
        self._find = scope['find']


class CompiledRouterNode(object):
    """Represents a single URI segment in a URI."""

    def __init__(self, raw_segment, method_map=None, resource=None):
        self.children = []

        self.raw_segment = raw_segment
        self.method_map = method_map
        self.resource = resource

        seg = raw_segment.replace('.', '\\.')
        matches = list(re.finditer('{([-_a-zA-Z0-9]*)}', seg))
        if matches:
            self.is_var = True
            # NOTE(richardolsson): if there is a single variable and it spans
            # the entire segment, the segment is uncomplex and the variable
            # name is simply the string contained within curly braces.
            if len(matches) == 1 and matches[0].span() == (0, len(seg)):
                self.is_complex = False
                self.var_name = raw_segment[1:-1]
            else:
                # NOTE(richardolsson): Complex segments need to be converted
                # into regular expressions will be used to match and extract
                # variable values. The regular expressions contain both
                # literal spans and named group expressions for the variables.
                self.is_complex = True
                seg_fields = []
                prev_end_idx = 0
                for match in matches:
                    var_start_idx, var_end_idx = match.span()
                    seg_fields.append(seg[prev_end_idx:var_start_idx])
                    var_name = match.groups()[0].replace('-', '_')
                    seg_fields.append('(?P<%s>[^/]*)' % var_name)
                    prev_end_idx = var_end_idx

                seg_fields.append(seg[prev_end_idx:])
                seg_pattern = ''.join(seg_fields)
                self.var_regex = re.compile(seg_pattern)
        else:
            self.is_var = False

    def matches(self, segment):
        """Returns True if this node matches the supplied URI segment."""

        if self.is_var:
            if self.is_complex:
                match = self.var_regex.search(segment)
                if match:
                    return True
                else:
                    return False
            else:
                return True
        elif segment == self.raw_segment:
            return True
        else:
            return False
