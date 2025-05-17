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

"""Routing utilities."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

from falcon import constants
from falcon import responders

if TYPE_CHECKING:
    from falcon._typing import AsgiResponderCallable
    from falcon._typing import MethodDict
    from falcon._typing import ResponderCallable


class SuffixedMethodNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super(SuffixedMethodNotFoundError, self).__init__(message)
        self.message = message


def map_http_methods(
    resource: object, suffix: Optional[str] = None, allow_on_request: bool = False
) -> MethodDict:
    """Map HTTP methods (e.g., GET, POST) to methods of a resource object.

    Args:
        resource: An object with *responder* methods, following the naming
            convention *on_\\**, that correspond to each method the resource
            supports. For example, if a resource supports GET and POST, it
            should define ``on_get(self, req, resp)`` and
            ``on_post(self, req, resp)``.

    Keyword Args:
        suffix (str): Optional responder name suffix for this route. If
            a suffix is provided, Falcon will map GET requests to
            ``on_get_{suffix}()``, POST requests to ``on_post_{suffix}()``,
            etc.
        allow_on_request (bool): If True, it prevents a
            ``SuffixedMethodNotFoundError`` from being raised on resources
            defining ``on_request_{suffix}()``.
            (See also: :ref:`CompiledRouterOptions <compiled_router_options>`.)


    Returns:
        dict: A mapping of HTTP methods to explicitly defined resource responders.

    """

    method_map = {}

    for method in constants.COMBINED_METHODS:
        try:
            responder_name = 'on_' + method.lower()
            if suffix:
                responder_name += '_' + suffix

            responder = getattr(resource, responder_name)
        except AttributeError:
            # resource does not implement this method
            pass
        else:
            # Usually expect a method, but any callable will do
            if callable(responder):
                method_map[method] = responder

    has_default_responder = allow_on_request and hasattr(
        resource, f'on_request_{suffix}'
    )

    # If suffix is specified and doesn't map to any methods, raise an error
    if suffix and not method_map and not has_default_responder:
        raise SuffixedMethodNotFoundError(
            'No responders found for the specified suffix'
        )

    return method_map


def set_default_responders(
    method_map: MethodDict,
    asgi: bool = False,
    default_responder: Optional[Union[ResponderCallable, AsgiResponderCallable]] = None,
) -> None:
    """Map HTTP methods not explicitly defined on a resource to default responders.

    Args:
        method_map: A dict with HTTP methods mapped to responders explicitly
            defined in a resource.
        asgi (bool): ``True`` if using an ASGI app, ``False`` otherwise
            (default ``False``).
        default_responder: An optional default responder for unimplemented
            resource methods (default: ``None``). If not provided, a new
            responder for "405 Method Not Allowed" is constructed.
    """

    # Attach a resource for unsupported HTTP methods
    allowed_methods = [
        m for m in sorted(list(method_map.keys())) if m not in constants._META_METHODS
    ]

    if 'OPTIONS' not in method_map:
        # OPTIONS itself is intentionally excluded from the Allow header
        opt_responder = responders.create_default_options(allowed_methods, asgi=asgi)
        method_map['OPTIONS'] = opt_responder  # type: ignore[assignment]
        allowed_methods.append('OPTIONS')

    if default_responder is None:
        default_responder = responders.create_method_not_allowed(
            allowed_methods, asgi=asgi
        )

    for method in constants.COMBINED_METHODS:
        if method not in method_map:
            method_map[method] = default_responder  # type: ignore[assignment]
