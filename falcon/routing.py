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

import re

import six

from falcon.hooks import _wrap_with_hooks
from falcon import HTTP_METHODS, responders


# NOTE(kgriffs): Published method; take care to avoid breaking changes.
def compile_uri_template(template):
    """Compile the given URI template string into a pattern matcher.

    This function currently only recognizes Level 1 URI templates, and only
    for the path portion of the URI.

    See also: http://tools.ietf.org/html/rfc6570

    Args:
        template: A Level 1 URI template. Method responders must accept, as
            arguments, all fields specified in the template (default '/').
            Note that field names are restricted to ASCII a-z, A-Z, and
            the underscore '_'.

    Returns:
        tuple: (template_field_names, template_regex)

    """

    if not isinstance(template, six.string_types):
        raise TypeError('uri_template is not a string')

    if not template.startswith('/'):
        raise ValueError("uri_template must start with '/'")

    if '//' in template:
        raise ValueError("uri_template may not contain '//'")

    if template != '/' and template.endswith('/'):
        template = template[:-1]

    expression_pattern = r'{([a-zA-Z][a-zA-Z_]*)}'

    # Get a list of field names
    fields = set(re.findall(expression_pattern, template))

    # Convert Level 1 var patterns to equivalent named regex groups
    escaped = re.sub(r'[\.\(\)\[\]\?\*\+\^\|]', r'\\\g<0>', template)
    pattern = re.sub(expression_pattern, r'(?P<\1>[^/]+)', escaped)
    pattern = r'\A' + pattern + r'\Z'

    return fields, re.compile(pattern, re.IGNORECASE)


# NOTE(kgriffs): Published method; take care to avoid breaking changes.
def create_http_method_map(resource, uri_fields, before, after):
    """Maps HTTP methods (e.g., GET, POST) to methods of a resource object.

    Args:
        resource: An object with *responder* methods, following the naming
            convention *on_\**, that correspond to each method the resource
            supports. For example, if a resource supports GET and POST, it
            should define ``on_get(self, req, resp)`` and
            ``on_post(self, req, resp)``.
        uri_fields: A set of field names from the route's URI template
            that a responder must support in order to avoid "method not
            allowed".
        before: An action hook or list of hooks to be called before each
            *on_\** responder defined by the resource.
        after: An action hook or list of hooks to be called after each
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
