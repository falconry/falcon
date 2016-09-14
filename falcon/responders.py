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

"""Default responder implementations."""

from falcon.errors import HTTPBadRequest
from falcon.errors import HTTPNotFound
from falcon.errors import HTTPMethodNotAllowed
from falcon.status_codes import HTTP_204


def path_not_found(req, resp, **kwargs):
    """Raise 404 HTTPNotFound error"""
    raise HTTPNotFound()


def bad_request(req, resp, **kwargs):
    """Raise 400 HTTPBadRequest error"""
    raise HTTPBadRequest('Bad request', 'Invalid HTTP method')


def create_method_not_allowed(allowed_methods):
    """Creates a responder for "405 Method Not Allowed"

    Args:
        allowed_methods: A list of HTTP methods (uppercase) that should be
            returned in the Allow header.

    """
    def method_not_allowed(req, resp, **kwargs):
        """Raise 405 HTTPMethodNotAllowed error"""
        raise HTTPMethodNotAllowed(allowed_methods)

    return method_not_allowed


def create_default_options(allowed_methods):
    """Creates a default responder for the OPTIONS method

    Args:
        allowed_methods: A list of HTTP methods (uppercase) that should be
            returned in the Allow header.

    """
    allowed = ', '.join(allowed_methods)

    def on_options(req, resp, **kwargs):
        resp.status = HTTP_204
        resp.set_header('Allow', allowed)
        resp.set_header('Content-Length', '0')

    return on_options
