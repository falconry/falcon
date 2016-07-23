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

import re

import six

from falcon import HTTP_METHODS, responders


# NOTE(kgriffs): Published method; take care to avoid breaking changes.
def compile_uri_template(template):
    """Compile the given URI template string into a pattern matcher.

    This function can be used to construct custom routing engines that
    iterate through a list of possible routes, attempting to match
    an incoming request against each route's compiled regular expression.

    Each field is converted to a named group, so that when a match
    is found, the fields can be easily extracted using
    :py:meth:`re.MatchObject.groupdict`.

    This function does not support the more flexible templating
    syntax used in the default router. Only simple paths with bracketed
    field expressions are recognized. For example::

        /
        /books
        /books/{isbn}
        /books/{isbn}/characters
        /books/{isbn}/characters/{name}

    Also, note that if the template contains a trailing slash character,
    it will be stripped in order to normalize the routing logic.

    Args:
        template(str): The template to compile. Note that field names are
            restricted to ASCII a-z, A-Z, and the underscore character.

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

    # template names should be able to start with A-Za-z
    # but also contain 0-9_ in the remaining portion
    expression_pattern = r'{([a-zA-Z]\w*)}'

    # Get a list of field names
    fields = set(re.findall(expression_pattern, template))

    # Convert Level 1 var patterns to equivalent named regex groups
    escaped = re.sub(r'[\.\(\)\[\]\?\*\+\^\|]', r'\\\g<0>', template)
    pattern = re.sub(expression_pattern, r'(?P<\1>[^/]+)', escaped)
    pattern = r'\A' + pattern + r'\Z'

    return fields, re.compile(pattern, re.IGNORECASE)


def create_http_method_map(resource):
    """Maps HTTP methods (e.g., 'GET', 'POST') to methods of a resource object.

    Args:
        resource: An object with *responder* methods, following the naming
            convention *on_\**, that correspond to each method the resource
            supports. For example, if a resource supports GET and POST, it
            should define ``on_get(self, req, resp)`` and
            ``on_post(self, req, resp)``.

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
                method_map[method] = responder

    # Attach a resource for unsupported HTTP methods
    allowed_methods = sorted(list(method_map.keys()))

    if 'OPTIONS' not in method_map:
        # OPTIONS itself is intentionally excluded from the Allow header
        opt_responder = responders.create_default_options(allowed_methods)
        method_map['OPTIONS'] = opt_responder
        allowed_methods.append('OPTIONS')

    na_responder = responders.create_method_not_allowed(allowed_methods)

    for method in HTTP_METHODS:
        if method not in allowed_methods:
            method_map[method] = na_responder

    return method_map
