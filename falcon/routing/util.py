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

from falcon import HTTP_METHODS, responders
from falcon.hooks import _wrap_with_hooks


def create_http_method_map(resource, before, after):
    """Maps HTTP methods (e.g., 'GET', 'POST') to methods of a resource object.

    Args:
        resource: An object with *responder* methods, following the naming
            convention *on_\**, that correspond to each method the resource
            supports. For example, if a resource supports GET and POST, it
            should define ``on_get(self, req, resp)`` and
            ``on_post(self, req, resp)``.
        before: An action hook or ``list`` of hooks to be called before each
            *on_\** responder defined by the resource.
        after: An action hook or ``list`` of hooks to be called after each
            *on_\** responder defined by the resource.

    Returns:
        dict: A mapping of HTTP methods to responders.

    """

    method_map = {}

    for method in HTTP_METHODS:
        try:
            responder = getattr(resource, 'on_' + method.lower())
        except AttributeError:
            # resource does not implement this method
            pass
        else:
            # Usually expect a method, but any callable will do
            if callable(responder):
                responder = _wrap_with_hooks(
                    before, after, responder, resource)
                method_map[method] = responder

    # Attach a resource for unsupported HTTP methods
    allowed_methods = sorted(list(method_map.keys()))

    # NOTE(sebasmagri): We want the OPTIONS and 405 (Not Allowed) methods
    # responders to be wrapped on global hooks
    if 'OPTIONS' not in method_map:
        # OPTIONS itself is intentionally excluded from the Allow header
        responder = responders.create_default_options(
            allowed_methods)
        method_map['OPTIONS'] = _wrap_with_hooks(
            before, after, responder, resource)
        allowed_methods.append('OPTIONS')

    na_responder = responders.create_method_not_allowed(allowed_methods)

    for method in HTTP_METHODS:
        if method not in allowed_methods:
            method_map[method] = _wrap_with_hooks(
                before, after, na_responder, resource)

    return method_map
