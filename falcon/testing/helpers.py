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

"""Testing utilities.

This module contains various testing utilities that can be accessed
directly from the `testing` package::

    from falcon import testing

    wsgi_environ = testing.create_environ()

"""

import cgi
import contextlib
import io
import itertools
import random
import sys

from falcon.util import compat, http_now, uri


# Constants
DEFAULT_HOST = 'falconframework.org'


# NOTE(kgriffs): Alias for backwards-compatibility with Falcon 0.2
httpnow = http_now


# get_encoding_from_headers() is Copyright 2016 Kenneth Reitz, and is
# used here under the terms of the Apache License, Version 2.0.
def get_encoding_from_headers(headers):
    """Returns encoding from given HTTP Header Dict.

    Args:
        headers(dict): Dictionary from which to extract encoding. Header
            names must either be lowercase or the dict must support
            case-insensitive lookups.
    """

    content_type = headers.get('content-type')

    if not content_type:
        return None

    content_type, params = cgi.parse_header(content_type)

    if 'charset' in params:
        return params['charset'].strip("'\"")

    if 'text' in content_type:
        return 'ISO-8859-1'

    return None


def rand_string(min, max):
    """Returns a randomly-generated string, of a random length.

    Args:
        min (int): Minimum string length to return, inclusive
        max (int): Maximum string length to return, inclusive

    """

    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord(' '), ord('~')))
                    for __ in range(string_length)])


def create_environ(path='/', query_string='', protocol='HTTP/1.1',
                   scheme='http', host=DEFAULT_HOST, port=None,
                   headers=None, app='', body='', method='GET',
                   wsgierrors=None, file_wrapper=None, remote_addr=None):

    """Creates a mock PEP-3333 environ ``dict`` for simulating WSGI requests.

    Keyword Args:
        path (str): The path for the request (default '/')
        query_string (str): The query string to simulate, without a
            leading '?' (default '')
        protocol (str): The HTTP protocol to simulate
            (default 'HTTP/1.1'). If set to 'HTTP/1.0', the Host header
            will not be added to the environment.
        scheme (str): URL scheme, either 'http' or 'https' (default 'http')
        host(str): Hostname for the request (default 'falconframework.org')
        port (str): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https').
        headers (dict): Headers as a ``dict`` or an iterable yielding
            (*key*, *value*) ``tuple``'s
        app (str): Value for the ``SCRIPT_NAME`` environ variable, described in
            PEP-333: 'The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This may be an empty string, if the
            application corresponds to the "root" of the server.' (default '')
        body (str): The body of the request (default ''). Accepts both byte
            strings and Unicode strings. Unicode strings are encoded as UTF-8
            in the request.
        method (str): The HTTP method to use (default 'GET')
        wsgierrors (io): The stream to use as *wsgierrors*
            (default ``sys.stderr``)
        file_wrapper: Callable that returns an iterable, to be used as
            the value for *wsgi.file_wrapper* in the environ.
        remote_addr (str): Remote address for the request (default '127.0.0.1')

    """

    if query_string and query_string.startswith('?'):
        raise ValueError("query_string should not start with '?'")

    body = io.BytesIO(body.encode('utf-8')
                      if isinstance(body, compat.text_type) else body)

    # NOTE(kgriffs): wsgiref, gunicorn, and uWSGI all unescape
    # the paths before setting PATH_INFO
    path = uri.decode(path, unquote_plus=False)

    if compat.PY3:
        # NOTE(kgriffs): The decoded path may contain UTF-8 characters.
        # But according to the WSGI spec, no strings can contain chars
        # outside ISO-8859-1. Therefore, to reconcile the URI
        # encoding standard that allows UTF-8 with the WSGI spec
        # that does not, WSGI servers tunnel the string via
        # ISO-8859-1. falcon.testing.create_environ() mimics this
        # behavior, e.g.:
        #
        #   tunnelled_path = path.encode('utf-8').decode('iso-8859-1')
        #
        # falcon.Request does the following to reverse the process:
        #
        #   path = tunnelled_path.encode('iso-8859-1').decode('utf-8', 'replace')
        #
        path = path.encode('utf-8').decode('iso-8859-1')

    if compat.PY2 and isinstance(path, compat.text_type):
        path = path.encode('utf-8')

    scheme = scheme.lower()
    if port is None:
        port = '80' if scheme == 'http' else '443'
    else:
        port = str(port)

    # NOTE(kgriffs): Judging by the algorithm given in PEP-3333 for
    # reconstructing the URL, SCRIPT_NAME is expected to contain a
    # preceding slash character.
    if app and not app.startswith('/'):
        app = '/' + app

    env = {
        'SERVER_PROTOCOL': protocol,
        'SERVER_SOFTWARE': 'gunicorn/0.17.0',
        'SCRIPT_NAME': app,
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'HTTP_USER_AGENT': 'curl/7.24.0 (x86_64-apple-darwin12.0)',
        'REMOTE_PORT': '65133',
        'RAW_URI': '/',
        'REMOTE_ADDR': remote_addr or '127.0.0.1',
        'SERVER_NAME': host,
        'SERVER_PORT': port,

        'wsgi.version': (1, 0),
        'wsgi.url_scheme': scheme,
        'wsgi.input': body,
        'wsgi.errors': wsgierrors or sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False
    }

    if file_wrapper is not None:
        env['wsgi.file_wrapper'] = file_wrapper

    if protocol != 'HTTP/1.0':
        host_header = host

        if scheme == 'https':
            if port != '443':
                host_header += ':' + port
        else:
            if port != '80':
                host_header += ':' + port

        env['HTTP_HOST'] = host_header

    content_length = body.seek(0, 2)
    body.seek(0)

    if content_length != 0:
        env['CONTENT_LENGTH'] = str(content_length)

    if headers is not None:
        _add_headers_to_environ(env, headers)

    return env


@contextlib.contextmanager
def redirected(stdout=sys.stdout, stderr=sys.stderr):
    """
    A context manager to temporarily redirect stdout or stderr

    e.g.:

    with redirected(stderr=os.devnull):
        ...
    """

    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    try:
        yield
    finally:
        sys.stderr, sys.stdout = old_stderr, old_stdout


def closed_wsgi_iterable(iterable):
    """Wraps an iterable to ensure its ``close()`` method is called.

    Wraps the given `iterable` in an iterator utilizing a ``for`` loop as
    illustrated in
    `the PEP-3333 server/gateway side example
    <https://www.python.org/dev/peps/pep-3333/#the-server-gateway-side>`_.
    Finally, if the iterable has a ``close()`` method, it is called upon
    exception or exausting iteration.

    Furthermore, the first bytestring yielded from iteration, if any, is
    prefetched before returning the wrapped iterator in order to ensure the
    WSGI ``start_response`` function is called even if the WSGI application is
    a generator.

    Args:
        iterable (iterable): An iterable that yields zero or more
            bytestrings, per PEP-3333

    Returns:
        iterator: An iterator yielding the same bytestrings as `iterable`
    """
    def wrapper():
        try:
            for item in iterable:
                yield item
        finally:
            if hasattr(iterable, 'close'):
                iterable.close()

    wrapped = wrapper()
    try:
        head = (next(wrapped),)
    except StopIteration:
        head = ()
    return itertools.chain(head, wrapped)


# ---------------------------------------------------------------------
# Private
# ---------------------------------------------------------------------


def _add_headers_to_environ(env, headers):
    if not isinstance(headers, dict):
        # Try to convert
        headers = dict(headers)

    for name, value in headers.items():
        name = name.upper().replace('-', '_')

        if value is None:
            value = ''
        else:
            value = value.strip()

        if name == 'CONTENT_TYPE':
            env[name] = value
        elif name == 'CONTENT_LENGTH':
            env[name] = value
        else:
            env['HTTP_' + name] = value
