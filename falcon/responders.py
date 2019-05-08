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

from functools import partial, update_wrapper

from falcon.errors import HTTPBadRequest
from falcon.errors import HTTPMethodNotAllowed
from falcon.errors import HTTPNotFound
from falcon.status_codes import HTTP_200


def path_not_found(req, resp, **kwargs):
    """Raise 404 HTTPNotFound error"""
    raise HTTPNotFound()


async def path_not_found_async(req, resp, **kwargs):
    """Raise 404 HTTPNotFound error"""
    raise HTTPNotFound()


def bad_request(req, resp, **kwargs):
    """Raise 400 HTTPBadRequest error"""
    raise HTTPBadRequest('Bad request', 'Invalid HTTP method')


async def bad_request_async(req, resp, **kwargs):
    """Raise 400 HTTPBadRequest error"""
    raise HTTPBadRequest('Bad request', 'Invalid HTTP method')


def method_not_allowed(allowed_methods, req, resp, **kwargs):
    """Raise 405 HTTPMethodNotAllowed error"""
    raise HTTPMethodNotAllowed(allowed_methods)


async def method_not_allowed_async(allowed_methods, req, resp, **kwargs):
    """Raise 405 HTTPMethodNotAllowed error"""
    raise HTTPMethodNotAllowed(allowed_methods)


def create_method_not_allowed(allowed_methods, asgi=False):
    """Create a responder for "405 Method Not Allowed"

    Args:
        allowed_methods: A list of HTTP methods (uppercase) that should be
            returned in the Allow header.
        asgi (bool): ``True`` if using an ASGI app, ``False`` otherwise
            (default ``False``).
    """

    if asgi:
        responder = method_not_allowed_async
    else:
        responder = method_not_allowed

    partial_method_not_allowed = partial(responder, allowed_methods)
    update_wrapper(partial_method_not_allowed, method_not_allowed)
    return partial_method_not_allowed


def on_options(allowed, req, resp, **kwargs):
    """Default options responder."""
    resp.status = HTTP_200
    resp.set_header('Allow', allowed)
    resp.set_header('Content-Length', '0')


async def on_options_async(allowed, req, resp, **kwargs):
    """Default options responder."""
    resp.status = HTTP_200
    resp.set_header('Allow', allowed)
    resp.set_header('Content-Length', '0')


def create_default_options(allowed_methods, asgi=False):
    """Create a default responder for the OPTIONS method

    Args:
        allowed_methods (iterable): An iterable of HTTP methods (uppercase)
            that should be returned in the Allow header.
        asgi (bool): ``True`` if using an ASGI app, ``False`` otherwise
            (default ``False``).
    """
    allowed = ', '.join(allowed_methods)

    if asgi:
        responder = on_options_async
    else:
        responder = on_options

    partial_on_options = partial(responder, allowed)
    update_wrapper(partial_on_options, on_options)
    return partial_on_options
