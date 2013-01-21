"""Includes private helpers for the API class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import re
from falcon import responders

HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'POST',
    'PUT',
    'TRACE'
)


def should_ignore_body(status, method):
    """Return True if the status or method indicates no body, per RFC 2616

    Args:
        status: An HTTP status line, e.g., "204 No Content"

    Returns:
        True if method is HEAD, or the status is 1xx, 204, or 304; returns
        False otherwise.

    """
    return (method == 'HEAD' or
            status.startswith('204') or
            status.startswith('1') or
            status.startswith('304'))


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

    if resp.body is not None:
        # Since body is assumed to be a byte string (str in Python 2, bytes in
        # Python 3), figure out the length using standard functions.
        resp.set_header('Content-Length', str(len(resp.body)))
    elif resp.stream is not None:
        if resp.stream_len is not None:
            # Total stream length is known in advance (e.g., streaming a file)
            resp.set_header('Content-Length', str(resp.stream_len))
        else:
            # Stream given, but length is unknown (dynamically-generated body)
            pass
    else:
        # No body given
        resp.set_header('Content-Length', '0')


def compile_uri_template(template):
    """Compile the given URI template string into a pattern matcher.

    Currently only recognizes Level 1 URI templates, and only for the path
    portion of the URI.

    See also: http://tools.ietf.org/html/rfc6570

    Args:
        template: A Level 1 URI template. Method responders can retrieve values
            for the fields specified as part of the template path by calling
            req.get_param(field_name)

    """
    if not isinstance(template, str):
        raise TypeError('uri_template is not a string')

    # Convert Level 1 var patterns to equivalent named regex groups
    escaped = re.sub(r'([\.\(\)\[\]\?\*\+\^\|])', r'\.', template)
    pattern = re.sub(r'{([a-zA-Z][a-zA-Z_]*)}', r'(?P<\1>[^/]+)', escaped)
    pattern = r'\A' + pattern + r'\Z'

    return re.compile(pattern, re.IGNORECASE)


def create_http_method_map(resource):
    """Maps HTTP methods (such as GET and POST) to methods of resource object

    Args:
        resource: An object with "responder" methods, starting with on_*, that
           correspond to each method the resource supports. For example, if a
           resource supports GET and POST, it should define
           on_get(self, req, resp) and on_post(self,req,resp).

    """
    method_map = {}

    for method in HTTP_METHODS:
        try:
            func = getattr(resource, 'on_' + method.lower())
        except AttributeError:
            # resource does not implement this method
            pass
        else:
            # Usually expect a method, but any callable will do
            if hasattr(func, '__call__'):
                method_map[method] = func

    # Attach a resource for unsupported HTTP methods
    allowed_methods = list(method_map.keys())
    func = responders.create_method_not_allowed(allowed_methods)

    for method in HTTP_METHODS:
        if method not in allowed_methods:
            method_map[method] = func

    return method_map
