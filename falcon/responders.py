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

from falcon.status_codes import HTTP_204
from falcon.status_codes import HTTP_400
from falcon.status_codes import HTTP_404
from falcon.status_codes import HTTP_405


def path_not_found(req, resp, **kwargs):
    """Simply sets responseto "404 Not Found", no body."""
    resp.status = HTTP_404


def bad_request(req, resp, **kwargs):
    """Sets response to "400 Bad Request", no body."""
    resp.status = HTTP_400


def create_method_not_allowed(allowed_methods):
    """Creates a responder for "405 Method Not Allowed"

    Args:
        allowed_methods: A list of HTTP methods (uppercase) that should be
            returned in the Allow header.

    """
    allowed = ', '.join(allowed_methods)

    def method_not_allowed(req, resp, **kwargs):
        resp.status = HTTP_405
        resp.set_header('Allow', allowed)

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

    return on_options
