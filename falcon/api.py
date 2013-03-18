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

from falcon.request import Request
from falcon.response import Response
import falcon.responders
from falcon.status_codes import HTTP_416
from falcon.api_helpers import *

from falcon.http_error import HTTPError
from falcon import DEFAULT_MEDIA_TYPE


class API(object):
    """Provides routing and such for building a web service application

    This class is the main entry point into a Falcon-based app. It provides a
    callable WSGI interface and a simple routing engine based on URI templates.

    """

    __slots__ = ('_after', '_before', '_media_type', '_routes')

    def __init__(self, media_type=DEFAULT_MEDIA_TYPE, before=None, after=None):
        """Initialize a new Falcon API instances

        Args:
            media_type: Default media type to use as the value for the
                Content-Type header on responses. (default 'application/json')
            before: A global action hook (or list of hooks) to call before
                each on_* responder, for all resources. Similar to the
                'falcon.before' decorator, but applies to the entire API. When
                more than one action function is given, they will be executed
                in natural order (starting with the first in the list).
            after: A global action hook (or list of hooks) to call after each
                on_* responder, for all resources. Similar to the 'after'
                decorator, but applies to the entire API.

        """

        self._routes = []
        self._media_type = media_type

        self._before = prepare_global_hooks(before)
        self._after = prepare_global_hooks(after)

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

        #
        # Set status and headers
        #
        use_body = not should_ignore_body(resp.status, req.method)
        if use_body:
            set_content_length(resp)
            body = get_body(resp)
        else:
            # Default: return an empty body
            body = []

        # Set content type if needed
        use_content_type = (body or
                            req.method == 'HEAD' or
                            resp.status == HTTP_416)

        if use_content_type:
            media_type = self._media_type
        else:
            media_type = None

        headers = resp._wsgi_headers(media_type)

        # Return the response per the WSGI spec
        start_response(resp.status, headers)
        return body

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

        path_template = compile_uri_template(uri_template)
        method_map = create_http_method_map(resource,
                                            self._before, self._after)

        # Insert at the head of the list in case we get duplicate
        # adds (will cause the last one to win).
        self._routes.insert(0, (path_template, method_map))

#----------------------------------------------------------------------------
# Helpers
#----------------------------------------------------------------------------

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
                    responder = falcon.responders.bad_request

                break
        else:
            responder = falcon.responders.path_not_found
            params = {}

        return (responder, params)
