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
import six

from falcon import DEFAULT_MEDIA_TYPE, HTTP_METHODS, responders
from falcon.hooks import _wrap_with_hooks
from falcon.http_error import HTTPError
from falcon.request import Request, RequestOptions
from falcon.response import Response
import falcon.responders
import falcon.status_codes as status

STREAM_BLOCK_SIZE = 8 * 1024  # 8 KiB

IGNORE_BODY_STATUS_CODES = set([
    status.HTTP_100,
    status.HTTP_101,
    status.HTTP_204,
    status.HTTP_304
])


class API(object):
    """This class is the main entry point into a Falcon-based app.

    Each API instance provides a callable WSGI interface and a simple routing
    engine based on URI Templates (RFC 6570).

    Args:
        media_type (str, optional): Default media type to use as the value for
            the Content-Type header on responses. (default 'application/json')
        before (callable, optional): A global action hook (or list of hooks)
            to call before each on_* responder, for all resources. Similar to
            the ``falcon.before`` decorator, but applies to the entire API.
            When more than one hook is given, they will be executed
            in natural order (starting with the first in the list).
        after (callable, optional): A global action hook (or list of hooks)
            to call after each on_* responder, for all resources. Similar to
            the ``after`` decorator, but applies to the entire API.
        middleware(callable class, optional): A global action middleware (or
            list of middlewares) to be executed wrapping the responder.
            Middleware object can define process_request and process_response,
            and they will be executed in natural order, as if they were round
            layers over responder:
                process_request is executed in the same order of definition
                process_response and process_exception in reversed order
            if you define middleware=[OutSideMw, InsideMw]
            the order will be:
                OutsideMw.process_request
                    InsideMw.process_request
                        responder
                    InsideMw.process_response
                OutsideMw.process_request
            Any exception would apply process_response of the unexecuted mw.
        request_type (Request, optional): Request-alike class to use instead
            of Falcon's default class. Useful if you wish to extend
            ``falcon.request.Request`` with a custom ``context_type``.
            (default falcon.request.Request)
        response_type (Response, optional): Response-alike class to use
            instead of Falcon's default class. (default
            falcon.response.Response)

    """

    __slots__ = ('_after', '_before', '_request_type', '_response_type',
                 '_error_handlers', '_media_type', '_routes', '_sinks',
                 '_serialize_error', 'req_options', '_middleware')

    def __init__(self, media_type=DEFAULT_MEDIA_TYPE, before=None, after=None,
                 request_type=Request, response_type=Response,
                 middleware=None):
        self._routes = []
        self._sinks = []
        self._media_type = media_type

        self._before = self._prepare_global_hooks(before)
        self._after = self._prepare_global_hooks(after)

        # set middleware
        self._middleware = self._prepare_mw(middleware)

        self._request_type = request_type
        self._response_type = response_type

        self._error_handlers = []
        self._serialize_error = self._default_serialize_error
        self.req_options = RequestOptions()

    def __call__(self, env, start_response):
        """WSGI `app` method.

        Makes instances of API callable from a WSGI server. May be used to
        host an API or called directly in order to simulate requests when
        testing the API.

        See also PEP 3333.

        Args:
            env (dict): A WSGI environment dictionary
            start_response (callable): A WSGI helper function for setting
                status and headers on a response.

        """

        req = self._request_type(env, options=self.req_options)
        resp = self._response_type()
        resource = None
        stack_mw = []  # Keep track of executed mw

        try:
            # NOTE(warsaw): Moved this to inside the try except because it's
            # possible when using object-based traversal for _get_responder()
            # to fail.  An example is a case where an object does not have the
            # requested next-hop child resource.  In that case, the object
            # being asked to dispatch to its child will raise an HTTP
            # exception signalling the problem, e.g. a 404.
            responder, params, resource = self._get_responder(req)
            # NOTE(kgriffs): Using an inner try..except in order to
            # address the case when err_handler raises HTTPError.
            #
            # NOTE(kgriffs): Coverage is giving false negatives,
            # so disabled on relevant lines. All paths are tested
            # afaict.
            try:
                # Run request middlewares and fill stack_mw
                self._call_req_mw(stack_mw, req, resp, params)

                responder(req, resp, **params)  # pragma: no cover
                # Run middlewares for response
                self._call_resp_mw(stack_mw, req, resp)
            except Exception as ex:
                for err_type, err_handler in self._error_handlers:
                    if isinstance(ex, err_type):
                        err_handler(ex, req, resp, params)
                        self._call_after_hooks(req, resp, resource)
                        self._call_resp_mw(stack_mw, req, resp)
                        break  # pragma: no cover

                else:
                    # PERF(kgriffs): This will propagate HTTPError to
                    # the handler below. It makes handling HTTPError
                    # less efficient, but that is OK since error cases
                    # don't need to be as fast as the happy path, and
                    # indeed, should perhaps be slower to create
                    # backpressure on clients that are issuing bad
                    # requests.
                    # NOTE(ealogar): This will executed remaining
                    # process_response when no error_handler is given
                    # and for whatever exception. If an HTTPError is raised
                    # remaining process_response will be executed later.
                    self._call_resp_mw(stack_mw, req, resp)
                    raise

        except HTTPError as ex:
            self._compose_error_response(req, resp, ex)
            self._call_after_hooks(req, resp, resource)
            self._call_resp_mw(stack_mw, req, resp)

        #
        # Set status and headers
        #
        use_body = not self._should_ignore_body(resp.status, req.method)
        if use_body:
            self._set_content_length(resp)
            body = self._get_body(resp, env.get('wsgi.file_wrapper'))
        else:
            # Default: return an empty body
            body = []

        # Set content type if needed
        use_content_type = (body or
                            req.method == 'HEAD' or
                            resp.status == status.HTTP_416)

        if use_content_type:
            media_type = self._media_type
        else:
            media_type = None

        headers = resp._wsgi_headers(media_type)

        # Return the response per the WSGI spec
        start_response(resp.status, headers)
        return body

    def add_route(self, uri_template, resource):
        """Associates a URI path with a resource.

        A resource is an instance of a class that defines various on_*
        "responder" methods, one for each HTTP method the resource
        allows. For example, to support GET, simply define an `on_get`
        responder. If a client requests an unsupported method, Falcon
        will respond with "405 Method not allowed".

        Responders must always define at least two arguments to receive
        request and response objects, respectively. For example::

            def on_post(self, req, resp):
                pass

        In addition, if the route's uri template contains field
        expressions, any responder that desires to receive requests
        for that route must accept arguments named after the respective
        field names defined in the template. For example, given the
        following uri template::

            /das/{thing}

        A PUT request to "/das/code" would be routed to::

            def on_put(self, req, resp, thing):
                pass

        Args:
            uri_template (str): Relative URI template. Currently only Level 1
                templates are supported. See also RFC 6570. Care must be
                taken to ensure the template does not mask any sink
                patterns (see also ``add_sink``).
            resource (instance): Object which represents an HTTP/REST
                "resource". Falcon will pass "GET" requests to on_get,
                "PUT" requests to on_put, etc. If any HTTP methods are not
                supported by your resource, simply don't define the
                corresponding request handlers, and Falcon will do the right
                thing.

        """

        uri_fields, path_template = self._compile_uri_template(uri_template)
        method_map = self._create_http_method_map(
            resource, uri_fields, self._before, self._after)

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._routes.insert(0, (path_template, method_map, resource))

    def add_sink(self, sink, prefix=r'/'):
        """Adds a "sink" responder to the API.

        If no route matches a request, but the path in the requested URI
        matches the specified prefix, Falcon will pass control to the
        given sink, regardless of the HTTP method requested.

        Args:
            sink (callable): A callable taking the form ``func(req, resp)``.

            prefix (str): A regex string, typically starting with '/', which
                will trigger the sink if it matches the path portion of the
                request's URI. Both strings and precompiled regex objects
                may be specified. Characters are matched starting at the
                beginning of the URI path.

                Note:
                    Named groups are converted to kwargs and passed to
                    the sink as such.

                Note:
                    If the route collides with a route's URI template, the
                    route will mask the sink (see also ``add_route``).

        """

        if not hasattr(prefix, 'match'):
            # Assume it is a string
            prefix = re.compile(prefix)

        # NOTE(kgriffs): Insert at the head of the list such that
        # in the case of a duplicate prefix, the last one added
        # is preferred.
        self._sinks.insert(0, (prefix, sink))

    def add_error_handler(self, exception, handler=None):
        """Adds a handler for a given exception type.

        Args:
            exception (type): Whenever an error occurs when handling a request
                that is an instance of this exception class, the given
                handler callable will be used to handle the exception.
            handler (callable): A callable taking the form
                ``func(ex, req, resp, params)``, called
                when there is a matching exception raised when handling a
                request.

                Note:
                    If not specified, the handler will default to
                    ``exception.handle``, where ``exception`` is the error
                    type specified above, and ``handle`` is a static method
                    (i.e., decorated with @staticmethod) that accepts
                    the same params just described.

                Note:
                    A handler can either raise an instance of HTTPError
                    or modify resp manually in order to communicate information
                    about the issue to the client.

        """

        if handler is None:
            try:
                handler = exception.handle
            except AttributeError:
                raise AttributeError('handler must either be specified '
                                     'explicitly or defined as a static'
                                     'method named "handle" that is a '
                                     'member of the given exception class.')

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the most recently added one to win).
        self._error_handlers.insert(0, (exception, handler))

    def set_error_serializer(self, serializer):
        """Override the default serializer for instances of HTTPError.

        When a responder raises an instance of HTTPError, Falcon converts
        it to an HTTP response automatically. The default serializer
        supports JSON and XML, but may be overridden by this method to
        use a custom serializer in order to support other media types.

        Note:
            If a custom media type is used and the type includes a
            "+json" or "+xml" suffix, the default serializer will
            convert the error to JSON or XML, respectively. If this
            is not desirable, a custom error serializer may be used
            to override this behavior.

        Args:
            serializer (callable): A function of the form
                ``func(req, exception)``, where `req` is the request
                object that was passed to the responder method, and
                `exception` is an instance of falcon.HTTPError.
                The function must return a tuple of the form
                ``(media_type, representation)``, or ``(None, None)``
                if the client does not support any of the
                available media types.

        """

        self._serialize_error = serializer

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    def _get_responder(self, req):
        """Searches routes for a matching responder.

        Args:
            req: The request object.

        Returns:
            A 3-member tuple consisting of a responder callable,
            a dict containing parsed path fields (if any were specified in
            the matching route's URI template), and a reference to the
            responder's resource instance.

        Note:
            If a responder was matched to the given URI, but the HTTP
            method was not found in the method_map for the responder,
            the responder callable element of the returned tuple will be
            `falcon.responder.bad_request`.

            Likewise, if no responder was matched for the given URI, then
            the responder callable element of the returned tuple will be
            `falcon.responder.path_not_found`
        """

        path = req.path
        method = req.method
        for path_template, method_map, resource in self._routes:
            m = path_template.match(path)
            if m:
                params = m.groupdict()

                try:
                    responder = method_map[method]
                except KeyError:
                    responder = falcon.responders.bad_request

                break
        else:
            params = {}
            resource = None

            for pattern, sink in self._sinks:
                m = pattern.match(path)
                if m:
                    params = m.groupdict()
                    responder = sink

                    break
            else:
                responder = falcon.responders.path_not_found

        return (responder, params, resource)

    def _compose_error_response(self, req, resp, error):
        """Composes a response for the given HTTPError instance."""

        resp.status = error.status

        if error.headers is not None:
            resp.set_headers(error.headers)

        if error.has_representation:
            media_type, body = self._serialize_error(req, error)

            if body is not None:
                resp.body = body

                # NOTE(kgriffs): This must be done AFTER setting the headers
                # from error.headers so that we will override Content-Type if
                # it was mistakenly set by the app.
                resp.content_type = media_type

    def _call_req_mw(self, stack_mw, req, resp, params):
        """Runs the process_request middleware and tracks"""

        for component in self._middleware:
            process_request, _ = component
            if process_request is not None:
                process_request(req, resp, params)

            # Put executed component on the stack
            stack_mw.append(component)  # keep track from outside

    def _call_resp_mw(self, stack_mw, req, resp):
        """Runs the process_response middleware and tracks"""

        while stack_mw:
            _, process_response = stack_mw.pop()
            if process_response is not None:
                process_response(req, resp)

    def _call_after_hooks(self, req, resp, resource):
        """Executes each of the global "after" hooks, in turn."""

        if not self._after:
            return

        for hook in self._after:
            try:
                hook(req, resp, resource)
            except TypeError:
                # NOTE(kgriffs): Catching the TypeError is a heuristic to
                # detect old hooks that do not accept the "resource" param
                hook(req, resp)

    @staticmethod
    def _prepare_global_hooks(hooks):
        if hooks is not None:
            if not isinstance(hooks, list):
                hooks = [hooks]

            for action in hooks:
                if not callable(action):
                    raise TypeError('One or more hooks are not callable')

        return hooks

    @staticmethod
    def _prepare_mw(middleware=None):
        """Check middleware interface and prepare it to iterate.

        Args:
            middleware:  list (or object) of input middleware

        Returns:
            A middleware list
        """

        # PERF(kgriffs): do getattr calls once, in advance, so we don't
        # have to do them every time in the request path.
        prepared_middleware = []

        if middleware is None:
            middleware = []
        else:
            if not isinstance(middleware, list):
                middleware = [middleware]

        for component in middleware:
            process_request = API._get_bound_method(component,
                                                    'process_request')
            process_response = API._get_bound_method(component,
                                                     'process_response')

            if not (process_request or process_response):
                msg = '{0} does not implement the middleware interface'
                raise TypeError(msg.format(component))

            prepared_middleware.append((process_request, process_response))

        return prepared_middleware

    @staticmethod
    def _get_bound_method(obj, method_name):
        """Get a bound method of the given object by name.

        Args:
            obj: Object on which to look up the method.
            method_name: Name of the method to retrieve.

        Returns:
            Bound method, or `None` if the method does not exist on`
            the object.

        """

        method = getattr(obj, method_name, None)
        if method is not None:
            # NOTE(kgriffs): Ensure it is a bound method
            if six.get_method_self(method) is None:  # pragma nocover
                # NOTE(kgriffs): In Python 3 this code is unreachable
                # because the above will raise AttributeError on its
                # own.
                msg = '{0} must be a bound method'.format(method)
                raise AttributeError(msg)

        return method

    @staticmethod
    def _should_ignore_body(status, method):
        """Return True if the status or method indicates no body per RFC 2616.

        Args:
            status: An HTTP status line, e.g., "204 No Content"

        Returns:
            True if method is HEAD, or the status is 1xx, 204, or 304; returns
            False otherwise.

        """

        return (method == 'HEAD' or status in IGNORE_BODY_STATUS_CODES)

    @staticmethod
    def _set_content_length(resp):
        """Set Content-Length when given a fully-buffered body or stream len.

        Pre:
            Either resp.body or resp.stream is set
        Post:
            resp contains a "Content-Length" header unless a stream is given,
                but resp.stream_len is not set (in which case, the length
                cannot be derived reliably).
        Args:
            resp: The response object on which to set the content length.

        """

        content_length = 0

        if resp.body_encoded is not None:
            # Since body is assumed to be a byte string (str in Python 2,
            # bytes in Python 3), figure out the length using standard
            # functions.
            content_length = len(resp.body_encoded)
        elif resp.data is not None:
            content_length = len(resp.data)
        elif resp.stream is not None:
            if resp.stream_len is not None:
                # Total stream length is known in advance
                content_length = resp.stream_len
            else:
                # Stream given, but length is unknown (dynamically-
                # generated body). Do not set the header.
                return -1

        resp.set_header('Content-Length', str(content_length))
        return content_length

    @staticmethod
    def _get_body(resp, wsgi_file_wrapper=None):
        """Converts resp content into an iterable as required by PEP 333

        Args:
            resp: Instance of falcon.Response
            wsgi_file_wrapper: Reference to wsgi.file_wrapper from the
                WSGI environ dict, if provided by the WSGI server. Used
                when resp.stream is a file-like object (default None).

        Returns:
            * If resp.body is not *None*, returns [resp.body], encoded
              as UTF-8 if it is a Unicode string. Bytestrings are returned
              as-is.
            * If resp.data is not *None*, returns [resp.data]
            * If resp.stream is not *None*, returns resp.stream
              iterable using wsgi.file_wrapper, if possible.
            * Otherwise, returns []

        """

        body = resp.body_encoded

        if body is not None:
            return [body]

        elif resp.data is not None:
            return [resp.data]

        elif resp.stream is not None:
            stream = resp.stream

            # NOTE(kgriffs): Heuristic to quickly check if
            # stream is file-like. Not perfect, but should be
            # good enough until proven otherwise.
            if hasattr(stream, 'read'):
                if wsgi_file_wrapper is not None:
                    # TODO(kgriffs): Make block size configurable at the
                    # global level, pending experimentation to see how
                    # useful that would be.
                    #
                    # See also the discussion on the PR: http://goo.gl/XGrtDz
                    return wsgi_file_wrapper(stream, STREAM_BLOCK_SIZE)
                else:
                    return iter(lambda: stream.read(STREAM_BLOCK_SIZE),
                                b'')

            return resp.stream

        return []

    @staticmethod
    def _default_serialize_error(req, exception):
        """Serialize the given instance of HTTPError.

        This function determines which of the supported media types, if
        any, are acceptable by the client, and serializes the error
        to the preferred type.

        Currently, JSON and XML are the only supported media types. If the
        client accepts both JSON and XML with equal weight, JSON will be
        chosen.

        Other media types can be supported by using a custom error serializer.

        Note:
            If a custom media type is used and the type includes a
            "+json" or "+xml" suffix, the error will be serialized
            to JSON or XML, respectively. If this behavior is not
            desirable, a custom error serializer may be used to
            override this one.

        Args:
            req: Instance of falcon.Request
            exception: Instance of falcon.HTTPError

        Returns:
            A tuple of the form ``(media_type, representation)``, or
            ``(None, None)`` if the client does not support any of the
            available media types.

        """
        representation = None

        preferred = req.client_prefers(('application/xml',
                                        'text/xml',
                                        'application/json'))

        if preferred is None:
            # NOTE(kgriffs): See if the client expects a custom media
            # type based on something Falcon supports. Returning something
            # is probably better than nothing, but if that is not
            # desired, this behavior can be customized by adding a
            # custom HTTPError serializer for the custom type.
            accept = req.accept.lower()

            # NOTE(kgriffs): Simple heuristic, but it's fast, and
            # should be sufficiently accurate for our purposes. Does
            # not take into account weights if both types are
            # acceptable (simply chooses JSON). If it turns out we
            # need to be more sophisticated, we can always change it
            # later (YAGNI).
            if '+json' in accept:
                preferred = 'application/json'
            elif '+xml' in accept:
                preferred = 'application/xml'

        if preferred is not None:
            if preferred == 'application/json':
                representation = exception.to_json()
            else:
                representation = exception.to_xml()

        return (preferred, representation)

    @staticmethod
    def _compile_uri_template(template):
        """Compile the given URI template string into a pattern matcher.

        Currently only recognizes Level 1 URI templates, and only for the path
        portion of the URI.

        See also: http://tools.ietf.org/html/rfc6570

        Args:
            template: A Level 1 URI template. Method responders must accept, as
                arguments, all fields specified in the template (default '/').
                Note that field names are restricted to ASCII a-z, A-Z, and
                the underscore '_'.

        Returns:
            (template_field_names, template_regex)

        """

        if not isinstance(template, six.string_types):
            raise TypeError('uri_template is not a string')

        if not template.startswith('/'):
            raise ValueError("uri_template must start with '/'")

        if '//' in template:
            raise ValueError("uri_template may not contain '//'")

        if template != '/' and template.endswith('/'):
            template = template[:-1]

        PCT_ENCODED = '%[0-9A-Fa-f]{2}'
        UNRESERVED = '[^/]'
        RESERVED = r'[:/\?#\[\]@\!\$&\'\(\)\*\+,;=]'
        BASIC_VARIABLE = '{([a-zA-Z]\w+)}'
        RESERVED_VARIABLE = r'{\+([a-zA-Z]\w+)}'

        # Get a list of field names
        fields = set(re.findall(BASIC_VARIABLE, template))
        fields.update(re.findall(RESERVED_VARIABLE, template))

        # Convert Basic and Reserved var patterns
        # to equivalent named regex groups
        escaped = re.sub(r'[\.\(\)\[\]\?\*\^\|]', r'\\\g<0>', template)
        pattern = re.sub(BASIC_VARIABLE, r'(?P<\1>%s+)' % UNRESERVED, escaped)
        pattern = re.sub(RESERVED_VARIABLE, r'(?P<\1>(%s|%s|%s)+)' %
                         (UNRESERVED, RESERVED, PCT_ENCODED), pattern)
        pattern = r'\A' + pattern + r'\Z'

        return fields, re.compile(pattern, re.IGNORECASE)

    @staticmethod
    def _create_http_method_map(resource, uri_fields, before, after):
        """Maps HTTP methods (e.g., GET, POST) to methods of a resource object.

        Args:
            resource: An object with "responder" methods, starting with
                on_*, that correspond to each method the resource supports.
                For example, if a resource supports GET and POST, it should
                define on_get(self, req, resp) and on_post(self,req,resp).
            uri_fields: A set of field names from the route's URI template
                that a responder must support in order to avoid "method not
                allowed".
            before: An action hook or list of hooks to be called before each
                on_* responder defined by the resource.
            after: An action hook or list of hooks to be called after each
                on_* responder defined by the resource.

        Returns:
            A tuple containing a dict mapping HTTP methods to responders,
            and the method-not-allowed responder.

        """

        method_map = {}

        for method in HTTP_METHODS:
            try:
                responder = getattr(resource, 'on_' + method.lower())
            except AttributeError:
                # resource does not implement this method
                pass
            else:
                # Usually expect a method, but any callable will do
                if callable(responder):
                    responder = _wrap_with_hooks(
                        before, after, responder, resource)
                    method_map[method] = responder

        # Attach a resource for unsupported HTTP methods
        allowed_methods = sorted(list(method_map.keys()))

        # NOTE(sebasmagri): We want the OPTIONS and 405 (Not Allowed) methods
        # responders to be wrapped on global hooks
        if 'OPTIONS' not in method_map:
            # OPTIONS itself is intentionally excluded from the Allow header
            responder = responders.create_default_options(
                allowed_methods)
            method_map['OPTIONS'] = _wrap_with_hooks(
                before, after, responder, resource)
            allowed_methods.append('OPTIONS')

        na_responder = responders.create_method_not_allowed(allowed_methods)

        for method in HTTP_METHODS:
            if method not in allowed_methods:
                method_map[method] = _wrap_with_hooks(
                    before, after, na_responder, resource)

        return method_map
