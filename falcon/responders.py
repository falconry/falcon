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

from __future__ import annotations

from typing import Any, Iterable, NoReturn, TYPE_CHECKING, Union

from falcon._typing import AsgiResponderCallable
from falcon._typing import ResponderCallable
from falcon.errors import HTTPBadRequest
from falcon.errors import HTTPMethodNotAllowed
from falcon.errors import HTTPRouteNotFound
from falcon.status_codes import HTTP_200

if TYPE_CHECKING:
    from falcon import Request
    from falcon import Response
    from falcon.asgi import Request as AsgiRequest
    from falcon.asgi import Response as AsgiResponse


def path_not_found(req: Request, resp: Response, **kwargs: Any) -> NoReturn:
    """Raise 404 HTTPRouteNotFound error."""
    raise HTTPRouteNotFound()


async def path_not_found_async(req: Request, resp: Response, **kwargs: Any) -> NoReturn:
    """Raise 404 HTTPRouteNotFound error."""
    raise HTTPRouteNotFound()


def bad_request(req: Request, resp: Response, **kwargs: Any) -> NoReturn:
    """Raise 400 HTTPBadRequest error."""
    raise HTTPBadRequest(title='Bad request', description='Invalid HTTP method')


async def bad_request_async(req: Request, resp: Response, **kwargs: Any) -> NoReturn:
    """Raise 400 HTTPBadRequest error."""
    raise HTTPBadRequest(title='Bad request', description='Invalid HTTP method')


def create_method_not_allowed(
    allowed_methods: Iterable[str], asgi: bool = False
) -> Union[ResponderCallable, AsgiResponderCallable]:
    """Create a responder for "405 Method Not Allowed".

    Args:
        allowed_methods: A list of HTTP methods (uppercase) that should be
            returned in the Allow header.
        asgi (bool): ``True`` if using an ASGI app, ``False`` otherwise
            (default ``False``).
    """

    if asgi:

        async def method_not_allowed_responder_async(
            req: AsgiRequest, resp: AsgiResponse, **kwargs: Any
        ) -> NoReturn:
            raise HTTPMethodNotAllowed(allowed_methods)

        return method_not_allowed_responder_async

    def method_not_allowed(req: Request, resp: Response, **kwargs: Any) -> NoReturn:
        raise HTTPMethodNotAllowed(allowed_methods)

    return method_not_allowed


def create_default_options(
    allowed_methods: Iterable[str], asgi: bool = False
) -> Union[ResponderCallable, AsgiResponderCallable]:
    """Create a default responder for the OPTIONS method.

    Args:
        allowed_methods (iterable): An iterable of HTTP methods (uppercase)
            that should be returned in the Allow header.
        asgi (bool): ``True`` if using an ASGI app, ``False`` otherwise
            (default ``False``).
    """
    allowed = ', '.join(allowed_methods)

    if asgi:

        async def options_responder_async(
            req: AsgiRequest, resp: AsgiResponse, **kwargs: Any
        ) -> None:
            resp.status = HTTP_200
            resp.set_header('Allow', allowed)
            resp.set_header('Content-Length', '0')

        return options_responder_async

    def options_responder(req: Request, resp: Response, **kwargs: Any) -> None:
        resp.status = HTTP_200
        resp.set_header('Allow', allowed)
        resp.set_header('Content-Length', '0')

    return options_responder
