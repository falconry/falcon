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

from falcon import responders, HTTP_METHODS
import falcon.status_codes as status
from falcon.hooks import _wrap_with_hooks

STREAM_BLOCK_SIZE = 8 * 1024  # 8 KiB

IGNORE_BODY_STATUS_CODES = set([
    status.HTTP_100,
    status.HTTP_101,
    status.HTTP_204,
    status.HTTP_304
])


def prepare_global_hooks(hooks):
    if hooks is not None:
        if not isinstance(hooks, list):
            hooks = [hooks]

        for action in hooks:
            if not callable(action):
                raise TypeError('One or more hooks are not callable')

    return hooks


def should_ignore_body(status, method):
    """Return True if the status or method indicates no body, per RFC 2616

    Args:
        status: An HTTP status line, e.g., "204 No Content"

    Returns:
        True if method is HEAD, or the status is 1xx, 204, or 304; returns
        False otherwise.

    """

    return (method == 'HEAD' or status in IGNORE_BODY_STATUS_CODES)


def set_content_length(resp):
    """Set Content-Length when given a fully-buffered body or stream length

    Pre:
        Either resp.body or resp.stream is set
    Post:
        resp contains a "Content-Length" header unless a stream is given, but
        resp.stream_len is not set (in which case, the length cannot be
            derived reliably).
    Args:
        resp: The response object on which to set the content length.

    """

    content_length = 0

    if resp.body_encoded is not None:
        # Since body is assumed to be a byte string (str in Python 2, bytes in
        # Python 3), figure out the length using standard functions.
        content_length = len(resp.body_encoded)
    elif resp.data is not None:
        content_length = len(resp.data)
    elif resp.stream is not None:
        if resp.stream_len is not None:
            # Total stream length is known in advance (e.g., streaming a file)
            content_length = resp.stream_len
        else:
            # Stream given, but length is unknown (dynamically-generated body)
            # ...do not set the header.
            return -1

    resp.set_header('Content-Length', str(content_length))
    return content_length


def get_body(resp, wsgi_file_wrapper=None):
    """Converts resp content into an iterable as required by PEP 333

    Args:
        resp: Instance of falcon.Response
        wsgi_file_wrapper: Reference to wsgi.file_wrapper from the
            WSGI environ dict, if provided by the WSGI server. Used
            when resp.stream is a file-like object (default None).

    Returns:
        * If resp.body is not *None*, returns [resp.body], encoded as UTF-8 if
          it is a Unicode string. Bytestrings are returned as-is.
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


def serialize_error(req, exception):
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
            representation = exception.json()
        else:
            representation = exception.xml()

    return (preferred, representation)


def compile_uri_template(template):
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

    expression_pattern = r'{([a-zA-Z][a-zA-Z_]*)}'

    # Get a list of field names
    fields = set(re.findall(expression_pattern, template))

    # Convert Level 1 var patterns to equivalent named regex groups
    escaped = re.sub(r'[\.\(\)\[\]\?\*\+\^\|]', r'\\\g<0>', template)
    pattern = re.sub(expression_pattern, r'(?P<\1>[^/]+)', escaped)
    pattern = r'\A' + pattern + r'\Z'

    return fields, re.compile(pattern, re.IGNORECASE)


def create_http_method_map(resource, uri_fields, before, after):
    """Maps HTTP methods (such as GET and POST) to methods of resource object

    Args:
        resource: An object with "responder" methods, starting with on_*, that
            correspond to each method the resource supports. For example, if a
            resource supports GET and POST, it should define
            on_get(self, req, resp) and on_post(self,req,resp).
        uri_fields: A set of field names from the route's URI template that
            a responder must support in order to avoid "method not allowed".
        before: An action hook or list of hooks to be called before each
            on_* responder defined by the resource.
        after: An action hook or list of hooks to be called after each on_*
            responder defined by the resource.

    Returns:
        A tuple containing a dict mapping HTTP methods to responders, and
        the method-not-allowed responder.

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
