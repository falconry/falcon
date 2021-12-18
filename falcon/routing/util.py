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

from falcon import constants
from falcon import responders
from falcon.util.deprecation import deprecated


class SuffixedMethodNotFoundError(Exception):
    def __init__(self, message):
        super(SuffixedMethodNotFoundError, self).__init__(message)
        self.message = message


# NOTE(kgriffs): Published method; take care to avoid breaking changes.
@deprecated('This method will be removed in Falcon 4.0.')
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

    Warning:
        If the template contains a trailing slash character, it will be
        stripped.

        Note that this is **different** from :ref:`the default behavior
        <trailing_slash_in_path>` of :func:`~falcon.App.add_route` used
        with the default :class:`~falcon.routing.CompiledRouter`.

        The :attr:`~falcon.RequestOptions.strip_url_path_trailing_slash`
        request option is not considered by ``compile_uri_template()``.


    Args:
        template(str): The template to compile. Note that field names are
            restricted to ASCII a-z, A-Z, and the underscore character.

    Returns:
        tuple: (template_field_names, template_regex)

    .. deprecated:: 3.1
    """

    if not isinstance(template, str):
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


def map_http_methods(resource, suffix=None):
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

    # If suffix is specified and doesn't map to any methods, raise an error
    if suffix and not method_map:
        raise SuffixedMethodNotFoundError(
            'No responders found for the specified suffix'
        )

    return method_map


def set_default_responders(method_map, asgi=False):
    """Map HTTP methods not explicitly defined on a resource to default responders.

    Args:
        method_map: A dict with HTTP methods mapped to responders explicitly
            defined in a resource.
        asgi (bool): ``True`` if using an ASGI app, ``False`` otherwise
            (default ``False``).
    """

    # Attach a resource for unsupported HTTP methods
    allowed_methods = [
        m for m in sorted(list(method_map.keys())) if m not in constants._META_METHODS
    ]

    if 'OPTIONS' not in method_map:
        # OPTIONS itself is intentionally excluded from the Allow header
        opt_responder = responders.create_default_options(allowed_methods, asgi=asgi)
        method_map['OPTIONS'] = opt_responder
        allowed_methods.append('OPTIONS')

    na_responder = responders.create_method_not_allowed(allowed_methods, asgi=asgi)

    for method in constants.COMBINED_METHODS:
        if method not in method_map:
            method_map[method] = na_responder
