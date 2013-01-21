"""Defines the API class.

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

import sys
import traceback

from .request import Request
from .response import Response
from . import responders
from .status_codes import *
from .api_helpers import *
from .http_error import HTTPError

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


class API(object):
    """Provides routing and such for building a web service application

    This class is the main entry point into a Falcon-based app. It provides a
    callable WSGI interface and a simple routing engine based on URI templates.

    """

    __slots__ = ('_routes')

    def __init__(self):
        """Initialize default values"""
        self._routes = []

    def __call__(self, env, start_response):
        """WSGI "app" method

        Makes instances of API callable by any WSGI server. See also PEP 333.

        Args:
            env: A WSGI environment dictionary
            start_response: A WSGI helper method for setting status and headers
                on a response.

        """

        req = Request(env)
        resp = Response()

        responder, params = self._get_responder(req.path, req.method)

        try:
            responder(req, resp, **params)

        except HTTPError as ex:
            resp.status = ex.status
            if ex.headers is not None:
                resp.set_headers(ex.headers)

            if req.client_accepts_json():
                resp.body = ex.json()

        except Exception as ex:
            # Reset to a known state and respond with a generic error
            req = Request(env)
            resp = Response()

            message = ['Responder raised ', ex.__class__.__name__]

            details = str(ex)
            if details:
                message.append(': ')
                message.append(details)

            stack = traceback.format_exc(sys.exc_info()[2])
            message.append('\n')
            message.append(stack)

            req.log_error(''.join(message))
            responders.server_error(req, resp)

        #
        # Set status and headers
        #
        use_body = not should_ignore_body(resp.status, req.method)
        if use_body:
            set_content_length(resp)

        start_response(resp.status, resp._wsgi_headers())

        # Return an iterable for the body, per the WSGI spec
        if use_body:
            if resp.body:
                return [resp.body]
            elif resp.stream is not None:
                return resp.stream

        # Default to returning an empty body
        return []

    def add_route(self, uri_template, resource):
        """Associate a URI path with a resource

        Args:
            uri_template: Relative URI template. Currently only Level 1
                templates are supported. See also RFC 6570.
            resource: Object which represents an HTTP/REST "resource". Falcon
                will pass "GET" requests to on_get, "PUT" requests to on_put,
                etc. If any HTTP methods are not supported by your resource,
                simply don't define the corresponding request handlers, and
                Falcon will do the right thing.

        """

        if not uri_template:
            uri_template = '/'

        path_template = compile_uri_template(uri_template)
        method_map = create_http_method_map(resource)

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._routes.insert(0, (path_template, method_map))

    def _get_responder(self, path, method):
        """Searches routes for a matching responder

        Args:
            path: URI path to search (without query stirng)
            method: HTTP method (uppercase) requested
        Returns:
            A 2-member tuple, containing a responder callable and a dict
            containing parsed path fields, if any were specified in
            the matching route's URI template

        """

        for path_template, method_map in self._routes:
            m = path_template.match(path)
            if m:
                params = m.groupdict()

                try:
                    responder = method_map[method]
                except KeyError:
                    responder = responders.bad_request

                break
        else:
            responder = responders.path_not_found
            params = {}

        return (responder, params)
