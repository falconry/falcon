# Copyright 2013 by Richard Olsson
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


TAB_STR = ' ' * 4


class CompiledRouter(object):
    """Fast URI router which compiles its routing logic to Python code.

    Generally you do not need to use this router class directly, as an
    instance is created by default when the falcon.API class is initialized.

    The router treats URI paths as a tree of URI segments and searches by
    checking the URI one segment at a time. Instead of interpreting the route
    tree for each look-up, it generates inlined, bespoke Python code to
    perform the search, then compiles that code. This makes the route
    processing quite fast.

    The generated code looks something like this::

        def find(path, return_values, expressions, params):
            path_len = len(path)
            if path_len > 0:
                if path[0] == "repos":
                    if path_len > 1:
                        params["org"] = path[1]
                        if path_len > 2:
                            params["repo"] = path[2]
                            if path_len > 3:
                                if path[3] == "commits":
                                    return return_values[3]
                                if path[3] == "compare":
                                    if path_len > 4:
                                        match = expressions[0].match(path[4])
                                        if match is not None:
                                            params.update(match.groupdict())
                                            if path_len > 5:
                                                if path[5] == "full":
                                                    return return_values[5]
                                                if path[5] == "part":
                                                    return return_values[6]
                                                return None
                                            return return_values[4]
                                        if path[4] == "all":
                                            return return_values[7]
                                        match = expressions[1].match(path[4])
                                        if match is not None:
                                            params.update(match.groupdict())
                                            if path_len > 5:
                                                if path[5] == "full":
                                                    return return_values[9]
                                                return None
                                            return return_values[8]
                                        return None
                                    return None
                                return None
                            return return_values[2]
                        return return_values[1]
                    return return_values[0]
                if path[0] == "teams":
                    if path_len > 1:
                        params["id"] = path[1]
                        if path_len > 2:
                            if path[2] == "members":
                                return return_values[11]
                            return None
                        return return_values[10]
                    return None
                if path[0] == "user":
                    if path_len > 1:
                        if path[1] == "memberships":
                            return return_values[12]
                        return None
                    return None
                if path[0] == "emojis":
                    if path_len > 1:
                        if path[1] == "signs":
                            if path_len > 2:
                                params["id"] = path[2]
                                return return_values[14]
                            return None
                        return None
                    return return_values[13]
                return None
            return None
    """

    def __init__(self):
        self._roots = []
        self._find = self._compile()
        self._code_lines = None
        self._src = None
        self._expressions = None
        self._return_values = None

    def add_route(self, uri_template, method_map, resource):
        """Adds a route between URI path template and resource."""
        # Can't start with a number, since these eventually get passed as
        # args to on_* responders
        if re.search('{\d', uri_template):
            raise ValueError('Field names may not start with a digit.')

        if re.search('\s', uri_template):
            raise ValueError('URI templates may not include whitespace.')

        path = uri_template.strip('/').split('/')

        def insert(nodes, path_index=0):
            for node in nodes:
                segment = path[path_index]
                if node.matches(segment):
                    path_index += 1
                    if path_index == len(path):
                        node.method_map = method_map
                        node.resource = resource
                    else:
                        insert(node.children, path_index)

                    return

                if node.conflicts_with(segment):
                    raise ValueError('The URI template for this route '
                                     "conflicts with another route's "
                                     'template.')

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
        self._find = self._compile()

    def find(self, uri):
        """Finds resource and method map for a URI, or returns None."""
        path = uri.lstrip('/').split('/')
        params = {}
        node = self._find(path, self._return_values, self._expressions, params)

        if node is not None:
            return node.resource, node.method_map, params
        else:
            return None, None, None

    def _compile_tree(self, nodes, indent=1, level=0):
        """Generates Python code for a routing tree or subtree."""

        def line(text, indent_offset=0):
            pad = TAB_STR * (indent + indent_offset)
            self._code_lines.append(pad + text)

        # NOTE(kgriffs): Base case
        if not nodes:
            return

        line('if path_len > %d:' % level)
        indent += 1

        level_indent = indent
        found_simple = False

        for node in nodes:
            if node.is_var:
                if node.is_complex:
                    # NOTE(richardolsson): Complex nodes are nodes which contain
                    # anything more than a single literal or variable, and they
                    # need to be checked using a pre-compiled regular expression.
                    expression_idx = len(self._expressions)
                    self._expressions.append(node.var_regex)

                    line('match = expressions[%d].match(path[%d]) # %s' % (
                        expression_idx, level, node.var_regex.pattern))

                    line('if match is not None:')
                    indent += 1
                    line('params.update(match.groupdict())')

                else:
                    # NOTE(kgriffs): Simple nodes just capture the entire path
                    # segment as the value for the param.
                    line('params["%s"] = path[%d]' % (node.var_name, level))

                    # NOTE(kgriffs): We don't allow multiple simple var nodes
                    # to exist at the same level, e.g.:
                    #
                    #   /foo/{id}/bar
                    #   /foo/{name}/bar
                    #
                    assert len(nodes) == 1
                    found_simple = True

            else:
                # NOTE(kgriffs): Not a param, so must match exactly
                line('if path[%d] == "%s":' % (level, node.raw_segment))
                indent += 1

            if node.resource is not None:
                # NOTE(kgriffs): This is a valid route, so we will want to
                # return the relevant information.
                resource_idx = len(self._return_values)
                self._return_values.append(node)

            self._compile_tree(node.children, indent, level + 1)

            if node.resource is None:
                line('return None')
            else:
                line('return return_values[%d]' % resource_idx)

            indent = level_indent

        if not found_simple:
            line('return None')

    def _compile(self):
        """Generates Python code for entire routing tree.

        The generated code is compiled and the resulting Python method is
        returned.
        """
        self._return_values = []
        self._expressions = []
        self._code_lines = [
            'def find(path, return_values, expressions, params):',
            TAB_STR + 'path_len = len(path)',
        ]

        self._compile_tree(self._roots)

        self._code_lines.append(
            # PERF(kgriffs): Explicit return of None is faster than implicit
            TAB_STR + 'return None'
        )

        self._src = '\n'.join(self._code_lines)

        scope = {}
        exec(compile(self._src, '<string>', 'exec'), scope)

        return scope['find']


class CompiledRouterNode(object):
    """Represents a single URI segment in a URI."""

    def __init__(self, raw_segment, method_map=None, resource=None):
        self.children = []

        self.raw_segment = raw_segment
        self.method_map = method_map
        self.resource = resource

        self.is_var = False
        self.is_complex = False
        self.var_name = None

        seg = raw_segment.replace('.', '\\.')

        matches = list(re.finditer('{([-_a-zA-Z0-9]+)}', seg))
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
                    seg_fields.append('(?P<%s>[^/]+)' % var_name)

                    prev_end_idx = var_end_idx

                seg_fields.append(seg[prev_end_idx:])
                seg_pattern = ''.join(seg_fields)
                self.var_regex = re.compile(seg_pattern)
        else:
            self.is_var = False

    @property
    def is_simple_var(self):
        return self.is_var and not self.is_complex

    def matches(self, segment):
        """Returns True if this node matches the supplied template segment."""

        return segment == self.raw_segment

    def conflicts_with(self, segment):
        """Returns True if this node conflicts with a given template segment."""

        # NOTE(kgriffs): This method assumes that the caller has already
        # checked if the segment matches. By definition, only unmatched
        # segments may conflict, so there isn't any sense in calling
        # conflicts_with in that case.
        assert not self.matches(segment)

        # NOTE(kgriffs): Possible combinations are as follows.
        #
        #   simple, simple ==> True
        #   simple, complex ==> True
        #   simple, string ==> True
        #   complex, simple ==> True
        #   complex, complex ==> False
        #   complex, string ==> False
        #   string, simple ==> True
        #   string, complex ==> False
        #   string, string ==> False
        #

        other = CompiledRouterNode(segment)

        if self.is_var:
            if self.is_complex:
                if other.is_complex:
                    return False

                if other.is_var:
                    return True

                return False
            else:
                # NOTE(kgriffs): Falcon does not support the following:
                #
                #   /foo/{thing1}
                #   /foo/{thing2}
                #
                # or
                #
                #   /foo/{thing1}
                #   /foo/all
                return True

        return other.is_simple_var
