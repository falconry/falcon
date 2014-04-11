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

from falcon import HTTP_200
from .helpers import rand_string


class TestResource:
    """Mock resource for integration testing.

    This class implements the *on_get* responder, captures
    request data, and sets response body and headers.

    Child classes may add additional methods and attributes as
    needed.

    Attributes:
        sample_status (str): HTTP status to set in the response
        sample_body (str): Random body string to set in the response
        resp_headers (dict): Sample headers to use in the response

        req (falcon.Request): Request object passed into the *on_get*
            responder
        resp (falcon.Response): Response object passed into the *on_get*
            responder
        kwargs (dict): Keyword arguments passed into the *on_get*
            responder, if any
        called (bool): True if *on_get* was ever called; False otherwise


    """

    sample_status = "200 OK"
    sample_body = rand_string(0, 128 * 1024)
    resp_headers = {
        'Content-Type': 'text/plain; charset=utf-8',
        'ETag': '10d4555ebeb53b30adf724ca198b32a2',
        'X-Hello': 'OH HAI'
    }

    def __init__(self):
        """Initializes called to False"""

        self.called = False

    def on_get(self, req, resp, **kwargs):
        """GET responder.

        Captures req, resp, and kwargs. Also sets up a sample response.

        Args:
            req: Falcon `Request` instance
            resp: Falcon `Response` instance
            kwargs: URI template *name=value* pairs, if any, along with
                any extra args injected by middleware

        """

        # Don't try this at home - classes aren't recreated
        # for every request
        self.req, self.resp, self.kwargs = req, resp, kwargs

        self.called = True
        resp.status = HTTP_200
        resp.body = self.sample_body
        resp.set_headers(self.resp_headers)
