"""Defines private helper functions for the Request class.

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

import re

QS_PATTERN = re.compile(r'([a-zA-Z_]+)=([^&]+)')


def parse_query_string(query_string):
    """Parse a query string into a dict

    Query string parameters are assumed to use standard form-encoding. Only
    parameters with values are parsed. for example, given "foo=bar&flag",
    this function would ignore "flag".

    Args:
        query_string: The query string to parse

    Returns:
        A dict containing (name, value) pairs, one per query parameter. Note
        that value will be a string, and that name is case-sensitive, both
        copied directly from the query string.

    Raises:
        TypeError: query_string was not a string or buffer

    """

    # PERF: use for loop in lieu of the dict constructor
    params = {}
    for k, v in QS_PATTERN.findall(query_string):
        if ',' in v:
            v = v.split(',')

        params[k] = v

    return params


def parse_headers(env):
    """Parse HTTP headers out of a WSGI environ dictionary

    Args:
        env: A WSGI environ dictionary

    Returns:
        A dict containing (name, value) pairs, one per HTTP header

    Raises:
        KeyError: The env dictionary did not contain a key that is required by
            PEP-333.
        TypeError: env is not dictionary-like. In other words, it has no
            attribute '__getitem__'.


    """

    # Parse HTTP_*
    headers = {}
    for key in env:
        if key.startswith('HTTP_'):
            headers[key[5:]] = env[key]

    # Per the WSGI spec, Content-Type is not under HTTP_*
    if 'CONTENT_TYPE' in env:
        headers['CONTENT_TYPE'] = env['CONTENT_TYPE']

    # Per the WSGI spec, Content-Length is not under HTTP_*
    if 'CONTENT_LENGTH' in env:
        headers['CONTENT_LENGTH'] = env['CONTENT_LENGTH']

    # Fallback to SERVER_* vars if the Host header isn't specified
    if 'HOST' not in headers:
        host = env['SERVER_NAME']
        port = env['SERVER_PORT']

        if port != '80':
            host = ''.join([host, ':', port])

        headers['HOST'] = host

    return headers
