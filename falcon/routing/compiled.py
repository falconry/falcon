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
import textwrap

from falcon.routing import converters
from falcon.routing.util import map_http_methods, set_default_responders
from falcon.util.compat import UserDict


_TAB_STR = ' ' * 4
_FIELD_PATTERN = re.compile(
    # NOTE(kgriffs): This disallows the use of the '}' character within
    # an argstr. However, we don't really have a way of escaping
    # curly brackets in URI templates at the moment, so users should
    # see this as a similar restriction and so somewhat unsurprising.
    #
    # We may want to create a contextual parser at some point to
    # work around this problem.
    r'{((?P<fname>[^}:]*)((?P<cname_sep>:(?P<cname>[^}\(]*))(\((?P<argstr>[^}]*)\))?)?)}'
)
_IDENTIFIER_PATTERN = re.compile('[A-Za-z_][A-Za-z0-9_]*$')


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
        '_converter_map',
        '_converters',
        '_find',
        '_finder_src',
        '_options',
        '_patterns',
        '_return_values',
        '_roots',
    )

    def __init__(self):
        self._ast = None
        self._converters = None
        self._finder_src = None

        self._options = CompiledRouterOptions()

        # PERF(kgriffs): This is usually an anti-pattern, but we do it
        # here to reduce lookup time.
        self._converter_map = self._options.converters.data

        self._patterns = None
        self._return_values = None
        self._roots = []

        # NOTE(kgriffs): Call _compile() last since it depends on
        # the variables above.
        self._find = self._compile()

    @property
    def options(self):
        return self._options

    @property
    def finder_src(self):
        return self._finder_src

    def map_http_methods(self, resource, **kwargs):
        """Map HTTP methods (e.g., GET, POST) to methods of a resource object.

        This method is called from :meth:`~.add_route` and may be overridden to
        provide a custom mapping strategy.

        Args:
            resource (instance): Object which represents a REST resource.
                The default maps the HTTP method ``GET`` to ``on_get()``,
                ``POST`` to ``on_post()``, etc. If any HTTP methods are not
                supported by your resource, simply don't define the
                corresponding request handlers, and Falcon will do the right
                thing.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route. If
                a suffix is provided, Falcon will map GET requests to
                ``on_get_{suffix}()``, POST requests to ``on_post_{suffix}()``,
                etc. In this way, multiple closely-related routes can be
                mapped to the same resource. For example, a single resource
                class can use suffixed responders to distinguish requests
                for a single item vs. a collection of those same items.
                Another class might use a suffixed responder to handle
                a shortlink route in addition to the regular route for the
                resource.
        """

        return map_http_methods(resource, suffix=kwargs.get('suffix', None))

    def add_route(self, uri_template, resource, **kwargs):
        """Adds a route between a URI path template and a resource.

        This method may be overridden to customize how a route is added.

        Args:
            uri_template (str): A URI template to use for the route
            resource (object): The resource instance to associate with
                the URI template.

        Keyword Args:
            suffix (str): Optional responder name suffix for this route. If
                a suffix is provided, Falcon will map GET requests to
                ``on_get_{suffix}()``, POST requests to ``on_post_{suffix}()``,
                etc. In this way, multiple closely-related routes can be
                mapped to the same resource. For example, a single resource
                class can use suffixed responders to distinguish requests
                for a single item vs. a collection of those same items.
                Another class might use a suffixed responder to handle
                a shortlink route in addition to the regular route for the
                resource.
        """

        method_map = self.map_http_methods(resource, **kwargs)
        set_default_responders(method_map)

        # NOTE(kgriffs): Fields may have whitespace in them, so sub
        # those before checking the rest of the URI template.
        if re.search(r'\s', _FIELD_PATTERN.sub('{FIELD}', uri_template)):
            raise ValueError('URI templates may not include whitespace.')

        path = uri_template.strip('/').split('/')

        used_names = set()
        for segment in path:
            self._validate_template_segment(segment, used_names)

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
                    msg = textwrap.dedent("""
                        The URI template for this route is inconsistent or conflicts with another
                        route's template. This is usually caused by configuring a field converter
                        differently for the same field in two different routes, or by using
                        different field names at the same level in the path (e.g.,
                        '/parents/{id}' and '/parents/{parent_id}/children')
                    """).strip().replace('\n', ' ')
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
        node = self._find(path, self._return_values, self._patterns,
                          self._converters, params)

        if node is not None:
            return node.resource, node.method_map, params, node.uri_template
        else:
            return None

    # -----------------------------------------------------------------
    # Private
    # -----------------------------------------------------------------

    def _validate_template_segment(self, segment, used_names):
        """Validates a single path segment of a URI template.

        1. Ensure field names are valid Python identifiers, since they
           will be passed as kwargs to responders.
        2. Check that there are no duplicate names, since that causes
           (at least) the following problems:

              a. For simple nodes, values from deeper nodes overwrite
                 values from more shallow nodes.
              b. For complex nodes, re.compile() raises a nasty error
        3. Check that when the converter syntax is used, the named
           converter exists.
        """

        for field in _FIELD_PATTERN.finditer(segment):
            name = field.group('fname')

            is_identifier = _IDENTIFIER_PATTERN.match(name)
            if not is_identifier or name in keyword.kwlist:
                msg_template = ('Field names must be valid identifiers '
                                '("{0}" is not valid)')
                msg = msg_template.format(name)
                raise ValueError(msg)

            if name in used_names:
                msg_template = ('Field names may not be duplicated '
                                '("{0}" was used more than once)')
                msg = msg_template.format(name)
                raise ValueError(msg)

            used_names.add(name)

            if field.group('cname_sep') == ':':
                msg = 'Missing converter for field "{0}"'.format(name)
                raise ValueError(msg)

            name = field.group('cname')
            if name and name not in self._converter_map:
                msg = 'Unknown converter: "{0}"'.format(name)
                raise ValueError(msg)

    def _generate_ast(self, nodes, parent, return_values, patterns, level=0, fast_return=True):
        """Generates a coarse AST for the router."""

        # NOTE(kgriffs): Base case
        if not nodes:
            return

        outer_parent = _CxIfPathLength('>', level)
        parent.append_child(outer_parent)
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
                    parent.append_child(construct)
                    parent = construct

                    if node.var_converter_map:
                        parent.append_child(_CxPrefetchGroupsFromPatternMatch())
                        parent = self._generate_conversion_ast(parent, node)

                    else:
                        parent.append_child(_CxSetParamsFromPatternMatch())

                else:
                    # NOTE(kgriffs): Simple nodes just capture the entire path
                    # segment as the value for the param.

                    if node.var_converter_map:
                        assert len(node.var_converter_map) == 1

                        parent.append_child(_CxSetFragmentFromPath(level))

                        field_name = node.var_name
                        __, converter_name, converter_argstr = node.var_converter_map[0]
                        converter_class = self._converter_map[converter_name]

                        converter_obj = self._instantiate_converter(
                            converter_class,
                            converter_argstr
                        )
                        converter_idx = len(self._converters)
                        self._converters.append(converter_obj)

                        construct = _CxIfConverterField(
                            field_name,
                            converter_idx,
                        )

                        parent.append_child(construct)
                        parent = construct
                    else:
                        parent.append_child(_CxSetParam(node.var_name, level))

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
                parent.append_child(construct)
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
                    parent.append_child(_CxReturnNone())
            else:
                # NOTE(kgriffs): Make sure that we have consumed all of
                # the segments for the requested route; otherwise we could
                # mistakenly match "/foo/23/bar" against "/foo/{id}".
                construct = _CxIfPathLength('==', level + 1)
                construct.append_child(_CxReturnValue(resource_idx))
                parent.append_child(construct)

                if fast_return:
                    parent.append_child(_CxReturnNone())

            parent = outer_parent

        if not found_simple and fast_return:
            parent.append_child(_CxReturnNone())

    def _generate_conversion_ast(self, parent, node):
        # NOTE(kgriffs): Unroll the converter loop into
        # a series of nested "if" constructs.
        for field_name, converter_name, converter_argstr in node.var_converter_map:
            converter_class = self._converter_map[converter_name]

            converter_obj = self._instantiate_converter(
                converter_class,
                converter_argstr
            )
            converter_idx = len(self._converters)
            self._converters.append(converter_obj)

            parent.append_child(_CxSetFragmentFromField(field_name))

            construct = _CxIfConverterField(
                field_name,
                converter_idx,
            )

            parent.append_child(construct)
            parent = construct

        # NOTE(kgriffs): Add remaining fields that were not
        # converted, if any.
        if node.num_fields > len(node.var_converter_map):
            parent.append_child(_CxSetParamsFromPatternMatchPrefetched())

        return parent

    def _compile(self):
        """Generates Python code for the entire routing tree.

        The generated code is compiled and the resulting Python method
        is returned.
        """

        src_lines = [
            'def find(path, return_values, patterns, converters, params):',
            _TAB_STR + 'path_len = len(path)',
        ]

        self._return_values = []
        self._patterns = []
        self._converters = []

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

    def _instantiate_converter(self, klass, argstr=None):
        if argstr is None:
            return klass()

        # NOTE(kgriffs): Don't try this at home. ;)
        src = '{0}({1})'.format(klass.__name__, argstr)
        return eval(src, {klass.__name__: klass})


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
        self.num_fields = 0

        # TODO(kgriffs): Rename these since the docs talk about "fields"
        # or "field expressions", not "vars" or "variables".
        self.var_name = None
        self.var_pattern = None
        self.var_converter_map = []

        # NOTE(kgriffs): CompiledRouter.add_route validates field names,
        # so here we can just assume they are OK and use the simple
        # _FIELD_PATTERN to match them.
        matches = list(_FIELD_PATTERN.finditer(raw_segment))

        if not matches:
            self.is_var = False
        else:
            self.is_var = True
            self.num_fields = len(matches)

            for field in matches:
                # NOTE(kgriffs): We already validated the field
                # expression to disallow blank converter names, or names
                # that don't match a known converter, so if a name is
                # given, we can just go ahead and use it.
                if field.group('cname'):
                    self.var_converter_map.append(
                        (
                            field.group('fname'),
                            field.group('cname'),
                            field.group('argstr'),
                        )
                    )

            if matches[0].span() == (0, len(raw_segment)):
                # NOTE(kgriffs): Single field, spans entire segment
                assert len(matches) == 1

                # TODO(kgriffs): It is not "complex" because it only
                # contains a single field. Rename this variable to make
                # it more descriptive.
                self.is_complex = False

                field = matches[0]
                self.var_name = field.group('fname')

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

                pattern_text = _FIELD_PATTERN.sub(r'(?P<\2>.+)', escaped_segment)
                pattern_text = '^' + pattern_text + '$'

                self.is_complex = True
                self.var_pattern = re.compile(pattern_text)

        if self.is_complex:
            assert self.is_var

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


class ConverterDict(UserDict):
    """A dict-like class for storing field converters."""

    def update(self, other):
        try:
            # NOTE(kgriffs): If it is a mapping type, it should
            # implement keys().
            names = other.keys()
        except AttributeError:
            # NOTE(kgriffs): Not a mapping type, so assume it is an
            # iterable of 2-item iterables. But we need to make it
            # re-iterable if it is a generator, for when we pass
            # it on to the parent's update().
            other = list(other)
            names = [n for n, __ in other]

        for n in names:
            self._validate(n)

        UserDict.update(self, other)

    def __setitem__(self, name, converter):
        self._validate(name)
        UserDict.__setitem__(self, name, converter)

    def _validate(self, name):
        if not _IDENTIFIER_PATTERN.match(name):
            raise ValueError(
                'Invalid converter name. Names may not be blank, and may '
                'only use ASCII letters, digits, and underscores. Names'
                'must begin with a letter or underscore.'
            )


class CompiledRouterOptions(object):
    """Defines a set of configurable router options.

    An instance of this class is exposed via :any:`API.router_options`
    for configuring certain :py:class:`~.CompiledRouter` behaviors.

    Attributes:
        converters: Represents the collection of named
            converters that may be referenced in URI template field
            expressions. Adding additional converters is simply a
            matter of mapping an identifier to a converter class::

                api.router_options.converters['mc'] = MyConverter

            The identifier can then be used to employ the converter
            within a URI template::

                api.add_route('/{some_field:mc}', some_resource)

            Converter names may only contain ASCII letters, digits,
            and underscores, and must start with either a letter or
            an underscore.

            Warning:

                Converter instances are shared between requests.
                Therefore, in threaded deployments, care must be taken
                to implement custom converters in a thread-safe
                manner.

            (See also: :ref:`Field Converters <routing_field_converters>`)
    """

    __slots__ = ('converters',)

    def __init__(self):
        self.converters = ConverterDict(
            (name, converter) for name, converter in converters.BUILTIN
        )


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

    def append_child(self, construct):
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
        lines = [
            '{0}match = patterns[{1}].match(path[{2}])  # {3}'.format(
                _TAB_STR * indentation,
                self._pattern_idx,
                self._segment_idx,
                self._pattern_text,
            ),
            '{0}if match is not None:'.format(_TAB_STR * indentation),
            self._children_src(indentation + 1),
        ]

        return '\n'.join(lines)


class _CxIfConverterField(_CxParent):
    def __init__(self, field_name, converter_idx):
        super(_CxIfConverterField, self).__init__()
        self._field_name = field_name
        self._converter_idx = converter_idx

    def src(self, indentation):
        lines = [
            '{0}field_value = converters[{1}].convert(fragment)'.format(
                _TAB_STR * indentation,
                self._converter_idx,
            ),
            '{0}if field_value is not None:'.format(_TAB_STR * indentation),
            "{0}params['{1}'] = field_value".format(
                _TAB_STR * (indentation + 1),
                self._field_name,
            ),
            self._children_src(indentation + 1),
        ]

        return '\n'.join(lines)


class _CxSetFragmentFromField(object):
    def __init__(self, field_name):
        self._field_name = field_name

    def src(self, indentation):
        return "{0}fragment = groups.pop('{1}')".format(
            _TAB_STR * indentation,
            self._field_name,
        )


class _CxSetFragmentFromPath(object):
    def __init__(self, segment_idx):
        self._segment_idx = segment_idx

    def src(self, indentation):
        return '{0}fragment = path[{1}]'.format(
            _TAB_STR * indentation,
            self._segment_idx,
        )


class _CxSetParamsFromPatternMatch(object):
    def src(self, indentation):
        return '{0}params.update(match.groupdict())'.format(
            _TAB_STR * indentation
        )


class _CxSetParamsFromPatternMatchPrefetched(object):
    def src(self, indentation):
        return '{0}params.update(groups)'.format(
            _TAB_STR * indentation
        )


class _CxPrefetchGroupsFromPatternMatch(object):
    def src(self, indentation):
        return '{0}groups = match.groupdict()'.format(
            _TAB_STR * indentation
        )


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
