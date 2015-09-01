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

from falcon import Request, Response
from falcon.testing import create_environ


class MiddlewareMock(object):
    """Mock object representing the middleware calling stack.

    Falcon Middleware has three potential steps. The MiddlewareMock allows
    the steps to be called individually in order to test the middleware
    outside of a normal WSGI call where the `process_response` may clean
    up values setup earlier by `process_request` or `process_resource`.

    MiddlewareMock applies the same rules on the middleware that the
    `falcon.API` does. That is, if `middleware` is a list of objects, then
    `process_response` runs the middleware in reverse order of either
    `process_request` or `process_resource` thereby simulating the order in
    which the middleware would run in a normal operation.

    Attributes:
        middleware (object or list, required): One or more objects
            (instantiated classes) that implement the Falcon Middleware
            specification. See `falcon.API` for details.
        env (dict): environment dictionary used to create the falcon.Request
            instance used for tests.
        path (string): URI path used for the `falcon.Request`
        protocol (str): HTTP protocol version, default 'HTTP/1.0'
        request_options (dict, optional): Options to pass to `falcon.Request`
        request (falcon.Request): instance of `falcon.Request` to use. If it
            is None or not an instance of `falcon.Request` then it will be
            created.
        resource (object): object instance that provides the resource that the
            routing would have normally provided. This is passed directly
            to the middleware for `process_resource` and `process_response`.
            It does not apply to `process_request`.
        response (falcon.Response): instance of `falcon.Response` to use. If it
            is None or not an instance of `falcon.Response` then it will be
            created.

    """

    def __init__(self):
        self.middleware = None
        self.env = None
        self.path = None
        self.protocol = 'HTTP/1.0'
        self.request_options = None
        self.request = None
        self.resource = None
        self.response = None

    def _build(self, **kwargs):
        """Create the request and response information"""
        if self.env is None:
            self.env = create_environ(
                path=self.path,
                protocol=self.protocol,
                **kwargs)

        # validate that self.request is an instance of falcon.Request
        # or reset it
        if self.request is not None:
            if not isinstance(self.request, Request):
                self.request = None
        if self.request is None:
            self.request = Request(self.env, self.request_options)

        # validate that self.response is an instance of falcon.Response
        # or reset it
        if self.response is not None:
            if not isinstance(self.response, Response):
                self.response = None
        if self.response is None:
            self.response = Response()

    def simulate_process_request(self, **kwargs):
        """Simulates running the middleware's `process_request`"""
        self._build(**kwargs)

        if isinstance(self.middleware, list):
            for m in self.middleware:
                if hasattr(m, 'process_request'):
                    m.process_request(self.request,
                                      self.response)
        elif hasattr(self.middleware, 'process_request'):
            self.middleware.process_request(self.request,
                                            self.response)
        else:
            raise TypeError(
                'middleware not configured or does not have the process_request')

    def simulate_process_resource(self, **kwargs):
        """Simulates running the middleware's `process_resource`"""
        self._build(**kwargs)

        if isinstance(self.middleware, list):
            for m in self.middleware:
                if hasattr(m, 'process_resource'):
                    m.process_resource(self.request,
                                       self.response,
                                       self.resource)
        elif hasattr(self.middleware, 'process_resource'):
            self.middleware.process_resource(self.request,
                                             self.response,
                                             self.resource)
        else:
            raise TypeError('middleware not configured')

    def simulate_process_response(self, **kwargs):
        """Simulates running the middleware's `process_response`"""
        self._build(**kwargs)

        if isinstance(self.middleware, list):
            reversed_middleware = self.middleware
            reversed_middleware.reverse()
            for m in reversed_middleware:
                if hasattr(m, 'process_response'):
                    m.process_response(self.request,
                                       self.response,
                                       self.resource)
        elif hasattr(self.middleware, 'process_response'):
            self.middleware.process_response(self.request,
                                             self.response,
                                             self.resource)
        else:
            raise TypeError('middleware not configured')
