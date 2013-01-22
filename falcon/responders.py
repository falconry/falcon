"""Default responders for handling common error cases.

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

from falcon.status_codes import *


def path_not_found(req, resp):
    """Simply sets responseto "404 Not Found", no body."""
    resp.status = HTTP_404


def bad_request(req, resp):
    """Sets response to "400 Bad Request", no body."""
    resp.status = HTTP_400


def server_error(req, resp):
    """Sets response to "500 Internal Server Error", no body."""
    resp.status = HTTP_500


def create_method_not_allowed(allowed_methods):
    """Creates a responder for "405 Method Not Allowed".ipyth

    Args:
        allowed_methods: A list of HTTP methods (uppercase) that should be
            returned in the Allow header.

    """

    def method_not_allowed(req, resp):
        resp.status = HTTP_405
        resp.set_header('Allow', ', '.join(allowed_methods))

    return method_not_allowed
