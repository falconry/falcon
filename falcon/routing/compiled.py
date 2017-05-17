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

"""Default routing engine."""

import keyword
import re


_FIELD_PATTERN = re.compile('{([^}]*)}')
_TAB_STR = ' ' * 4


class CompiledRouter(object):
    """Fast URI router which compiles its routing logic to Python code.

    Generally you do not need to use this router class directly, as an
    instance is created by default when the falcon.API class is initialized.

    The router treats URI paths as a tree of URI segments and searches by
    checking the URI one segment at a time. Instead of interpreting the route
    tree for each look-up, it generates inlined, bespoke Python code to
    perform the search, then compiles that code. This makes the route
    processing quite fast.
    """

    __slots__ = (
        '_ast',
        '_find',
        '_finder_src',
        '_patterns',
        '_return_values',
        '_roots',
    )

    def __init__(self):
        self._roots = []
        self._find = self._compile()
        self._finder_src = None
        self._patterns = None
        self._return_values = None

    @property
    def finder_src(self):
        return self._finder_src

    def add_route(self, uri_template, method_map, resource):
        """Adds a route between a URI path template and a resource.

        Args:
            uri_template (str): A URI template to use for the route
            method_map (dict): A mapping of HTTP methods (e.g., 'GET',
                'POST') to methods of a resource object.
            resource (object): The resource instance to associate with
                the URI template.
        """

        if re.search('\s', uri_template):
            raise ValueError('URI templates may not include whitespace.')

        # NOTE(kgriffs): Ensure fields are valid Python identifiers,
        # since they will be passed as kwargs to responders. Also
        # ensure there are no duplicate names, since that causes the
        # following problems:
        #
        #   1. For simple nodes, values from deeper nodes overwrite
        #      values from more shallow nodes.
        #   2. For complex nodes, re.compile() raises a nasty error
        #
        fields = _FIELD_PATTERN.findall(uri_template)
        used_names = set()
        for name in fields:
            is_identifier = re.match('[A-Za-z_][A-Za-z0-9_]*$', name)
            if not is_identifier or name in keyword.kwlist:
                raise ValueError('Field names must be valid identifiers '
                                 "('{}' is not valid).".format(name))

            if name in used_names:
                raise ValueError('Field names may not be duplicated '
                                 "('{}' was used more than once)".format(name))

            used_names.add(name)

        path = uri_template.strip('/').split('/')

        def insert(nodes, path_index=0):
            for node in nodes:
                segment = path[path_index]
                if node.matches(segment):
                    path_index += 1
                    if path_index == len(path):
                        # NOTE(kgriffs): Override previous node
                        node.method_map = method_map
                        node.resource = resource
                        node.uri_template = uri_template
                    else:
                        insert(node.children, path_index)

                    return

                if node.conflicts_with(segment):
                    msg = (
                        'The URI template for this route conflicts with another'
                        "route's template. This is usually caused by using "
                        'different field names at the same level in the path. '
                        'For example, given the route paths '
                        "'/parents/{id}' and '/parents/{parent_id}/children', "
                        'the conflict can be resolved by renaming one of the '
                        'fields to match the other, i.e.: '
                        "'/parents/{parent_id}' and '/parents/{parent_id}/children'."
                    )
                    raise ValueError(msg)

            # NOTE(richardolsson): If we got this far, the node doesn't already
            # exist and needs to be created. This builds a new branch of the
            # routing tree recursively until it reaches the new node leaf.
            new_node = CompiledRouterNode(path[path_index])
            nodes.append(new_node)
            if path_index == len(path) - 1:
                new_node.method_map = method_map
                new_node.resource = resource
                new_node.uri_template = uri_template
            else:
                insert(new_node.children, path_index + 1)

        insert(self._roots)
        self._find = self._compile()

    def find(self, uri, req=None):
        """Search for a route that matches the given partial URI.

        Args:
            uri(str): The requested path to route.

        Keyword Args:
            req(Request): The Request object that will be passed to
                the routed responder. Currently the value of this
                argument is ignored by :class:`~.CompiledRouter`.
                Routing is based solely on the path.

        Returns:
            tuple: A 4-member tuple composed of (resource, method_map,
                params, uri_template), or ``None`` if no route matches
                the requested path.
        """

        path = uri.lstrip('/').split('/')
        params = {}
        node = self._find(path, self._return_values, self._patterns, params)

        if node is not None:
            return node.resource, node.method_map, params, node.uri_template
        else:
            return None

    # -----------------------------------------------------------------
    # Private
    # -----------------------------------------------------------------

    def _generate_ast(self, nodes, parent, return_values, patterns, level=0, fast_return=True):
        """Generates a coarse AST for the router."""

        # NOTE(kgriffs): Base case
        if not nodes:
            return

        outer_parent = _CxIfPathLength('>', level)
        parent.append(outer_parent)
        parent = outer_parent

        found_simple = False

        # NOTE(kgriffs & philiptzou): Sort nodes in this sequence:
        # static nodes(0), complex var nodes(1) and simple var nodes(2).
        # so that none of them get masked.
        nodes = sorted(
            nodes, key=lambda node: node.is_var + (node.is_var and
                                                   not node.is_complex))

        # NOTE(kgriffs): Down to this branch in the tree, we can do a
        # fast 'return None'. See if the nodes at this branch are
        # all still simple, meaning there is only one possible path.
        if fast_return:
            if len(nodes) > 1:
                # NOTE(kgriffs): There's the possibility of more than
                # one path.
                var_nodes = [node for node in nodes if node.is_var]
                found_var_nodes = bool(var_nodes)

                fast_return = not found_var_nodes

        for node in nodes:
            if node.is_var:
                if node.is_complex:
                    # NOTE(richardolsson): Complex nodes are nodes which
                    # contain anything more than a single literal or variable,
                    # and they need to be checked using a pre-compiled regular
                    # expression.
                    pattern_idx = len(patterns)
                    patterns.append(node.var_pattern)

                    construct = _CxIfPathSegmentPattern(level, pattern_idx,
                                                        node.var_pattern.pattern)
                    parent.append(construct)
                    parent = construct

                else:
                    # NOTE(kgriffs): Simple nodes just capture the entire path
                    # segment as the value for the param.
                    parent.append(_CxSetParam(node.var_name, level))

                    # NOTE(kgriffs): We don't allow multiple simple var nodes
                    # to exist at the same level, e.g.:
                    #
                    #   /foo/{id}/bar
                    #   /foo/{name}/bar
                    #
                    assert len([_node for _node in nodes
                                if _node.is_var and not _node.is_complex]) == 1
                    found_simple = True

            else:
                # NOTE(kgriffs): Not a param, so must match exactly
                construct = _CxIfPathSegmentLiteral(level, node.raw_segment)
                parent.append(construct)
                parent = construct

            if node.resource is not None:
                # NOTE(kgriffs): This is a valid route, so we will want to
                # return the relevant information.
                resource_idx = len(return_values)
                return_values.append(node)

            self._generate_ast(
                node.children,
                parent,
                return_values,
                patterns,
                level + 1,
                fast_return
            )

            if node.resource is None:
                if fast_return:
                    parent.append(_CxReturnNone())
            else:
                # NOTE(kgriffs): Make sure that we have consumed all of
                # the segments for the requested route; otherwise we could
                # mistakenly match "/foo/23/bar" against "/foo/{id}".
                construct = _CxIfPathLength('==', level + 1)
                construct.append(_CxReturnValue(resource_idx))
                parent.append(construct)

                if fast_return:
                    parent.append(_CxReturnNone())

            parent = outer_parent

        if not found_simple and fast_return:
            parent.append(_CxReturnNone())

    def _compile(self):
        """Generates Python code for the entire routing tree.

        The generated code is compiled and the resulting Python method
        is returned.
        """

        src_lines = [
            'def find(path, return_values, patterns, params):',
            _TAB_STR + 'path_len = len(path)',
        ]

        self._return_values = []
        self._patterns = []

        self._ast = _CxParent()
        self._generate_ast(
            self._roots,
            self._ast,
            self._return_values,
            self._patterns
        )

        src_lines.append(self._ast.src(0))

        src_lines.append(
            # PERF(kgriffs): Explicit return of None is faster than implicit
            _TAB_STR + 'return None'
        )

        self._finder_src = '\n'.join(src_lines)

        scope = {}
        exec(compile(self._finder_src, '<string>', 'exec'), scope)

        return scope['find']


class CompiledRouterNode(object):
    """Represents a single URI segment in a URI."""

    def __init__(self, raw_segment,
                 method_map=None, resource=None, uri_template=None):
        self.children = []

        self.raw_segment = raw_segment
        self.method_map = method_map
        self.resource = resource
        self.uri_template = uri_template

        self.is_var = False
        self.is_complex = False
        self.var_name = None
        self.var_pattern = None

        # NOTE(kgriffs): CompiledRouter.add_route validates field names,
        # so here we can just assume they are OK and use the simple
        # _FIELD_PATTERN to match them.
        matches = list(_FIELD_PATTERN.finditer(raw_segment))

        if not matches:
            self.is_var = False
        else:
            self.is_var = True

            if len(matches) == 1 and matches[0].span() == (0, len(raw_segment)):
                # NOTE(richardolsson): if there is a single variable and
                # it spans the entire segment, the segment is not
                # complex and the variable name is simply the string
                # contained within curly braces.
                self.is_complex = False
                self.var_name = raw_segment[1:-1]
            else:
                # NOTE(richardolsson): Complex segments need to be
                # converted into regular expressions in order to match
                # and extract variable values. The regular expressions
                # contain both literal spans and named group expressions
                # for the variables.

                # NOTE(kgriffs): Don't use re.escape() since we do not
                # want to escape '{' or '}', and we don't want to
                # introduce any unexpected side-effects by escaping
                # non-ASCII characters (it is probably safe, but let's
                # not take that chance in a minor point release).
                #
                # NOTE(kgriffs): The substitution template parser in the
                # re library does not look ahead when collapsing '\\':
                # therefore in the case of r'\\g<0>' the first r'\\'
                # would be consumed and collapsed to r'\', and then the
                # parser would examine 'g<0>' and not realize it is a
                # group-escape sequence. So we add an extra backslash to
                # trick the parser into doing the right thing.
                escaped_segment = re.sub(r'[\.\(\)\[\]\?\$\*\+\^\|]', r'\\\g<0>', raw_segment)

                pattern_text = _FIELD_PATTERN.sub(r'(?P<\1>.+)', escaped_segment)
                pattern_text = '^' + pattern_text + '$'

                self.is_complex = True
                self.var_pattern = re.compile(pattern_text)

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
        #   simple, complex ==> False
        #   simple, string ==> False
        #   complex, simple ==> False
        #   complex, complex ==> (Maybe)
        #   complex, string ==> False
        #   string, simple ==> False
        #   string, complex ==> False
        #   string, string ==> False
        #
        other = CompiledRouterNode(segment)

        if self.is_var:
            # NOTE(kgriffs & philiptzou): Falcon does not accept multiple
            # simple var nodes exist at the same level as following:
            #
            #   /foo/{thing1}
            #   /foo/{thing2}
            #
            # Nor two complex nodes like this:
            #
            #   /foo/{thing1}.{ext}
            #   /foo/{thing2}.{ext}
            #
            # On the other hand, those are all OK:
            #
            #   /foo/{thing1}
            #   /foo/all
            #   /foo/{thing1}.{ext}
            #   /foo/{thing2}.detail.{ext}
            #
            if self.is_complex:
                if other.is_complex:
                    return (_FIELD_PATTERN.sub('v', self.raw_segment) ==
                            _FIELD_PATTERN.sub('v', segment))

                return False
            else:
                return other.is_var and not other.is_complex

        # NOTE(kgriffs): If self is a static string match, then all the cases
        # for other are False, so no need to check.
        return False


# --------------------------------------------------------------------
# AST Constructs
#
# NOTE(kgriffs): These constructs are used to create a very coarse
#   AST that can then be used to generate Python source code for the
#   router. Using an AST like this makes it easier to reason about
#   the compilation process, and affords syntactical transformations
#   that would otherwise be at best confusing and at worst extremely
#   tedious and error-prone if they were to be attempted directly
#   against the Python source code.
# --------------------------------------------------------------------


class _CxParent(object):
    def __init__(self):
        self._children = []

    def append(self, construct):
        self._children.append(construct)

    def src(self, indentation):
        return self._children_src(indentation + 1)

    def _children_src(self, indentation):
        src_lines = [
            child.src(indentation)
            for child in self._children
        ]

        return '\n'.join(src_lines)


class _CxIfPathLength(_CxParent):
    def __init__(self, comparison, length):
        super(_CxIfPathLength, self).__init__()
        self._comparison = comparison
        self._length = length

    def src(self, indentation):
        template = '{0}if path_len {1} {2}:\n{3}'
        return template.format(
            _TAB_STR * indentation,
            self._comparison,
            self._length,
            self._children_src(indentation + 1)
        )


class _CxIfPathSegmentLiteral(_CxParent):
    def __init__(self, segment_idx, literal):
        super(_CxIfPathSegmentLiteral, self).__init__()
        self._segment_idx = segment_idx
        self._literal = literal

    def src(self, indentation):
        template = "{0}if path[{1}] == '{2}':\n{3}"
        return template.format(
            _TAB_STR * indentation,
            self._segment_idx,
            self._literal,
            self._children_src(indentation + 1)
        )


class _CxIfPathSegmentPattern(_CxParent):
    def __init__(self, segment_idx, pattern_idx, pattern_text):
        super(_CxIfPathSegmentPattern, self).__init__()
        self._segment_idx = segment_idx
        self._pattern_idx = pattern_idx
        self._pattern_text = pattern_text

    def src(self, indentation):
        lines = []

        lines.append(
            '{0}match = patterns[{1}].match(path[{2}])  # {3}'.format(
                _TAB_STR * indentation,
                self._pattern_idx,
                self._segment_idx,
                self._pattern_text,
            )
        )

        lines.append('{0}if match is not None:'.format(_TAB_STR * indentation))
        lines.append('{0}params.update(match.groupdict())'.format(
            _TAB_STR * (indentation + 1)
        ))

        lines.append(self._children_src(indentation + 1))

        return '\n'.join(lines)


class _CxReturnNone(object):
    def src(self, indentation):
        return '{0}return None'.format(_TAB_STR * indentation)


class _CxReturnValue(object):
    def __init__(self, value_idx):
        self._value_idx = value_idx

    def src(self, indentation):
        return '{0}return return_values[{1}]'.format(
            _TAB_STR * indentation,
            self._value_idx
        )


class _CxSetParam(object):
    def __init__(self, param_name, segment_idx):
        self._param_name = param_name
        self._segment_idx = segment_idx

    def src(self, indentation):
        return "{0}params['{1}'] = path[{2}]".format(
            _TAB_STR * indentation,
            self._param_name,
            self._segment_idx,
        )
