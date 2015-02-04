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

import random
import io
import sys
from datetime import datetime

import six

import falcon
from falcon.util import uri

# Constants
DEFAULT_HOST = 'falconframework.org'


def httpnow():
    """Returns the current UTC time as an RFC 1123 date.

    Returns:
        str: An HTTP date string, e.g., "Tue, 15 Nov 1994 12:45:26 GMT".

    """

    return falcon.dt_to_http(datetime.utcnow())


def rand_string(min, max):
    """Returns a randomly-generated string, of a random length.

    Args:
        min (int): Minimum string length to return, inclusive
        max (int): Maximum string length to return, inclusive

    """

    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord(' '), ord('~')))
                    for i in range(string_length)])


def create_environ(path='/', query_string='', protocol='HTTP/1.1',
                   scheme='http', host=DEFAULT_HOST, port=None,
                   headers=None, app='', body='', method='GET',
                   wsgierrors=None, file_wrapper=None):

    """Creates a mock PEP-3333 environ ``dict`` for simulating WSGI requests.

    Args:
        path (str, optional): The path for the request (default '/')
        query_string (str, optional): The query string to simulate, without a
            leading '?' (default '')
        protocol (str, optional): The HTTP protocol to simulate
            (default 'HTTP/1.1'). If set to 'HTTP/1.0', the Host header
            will not be added to the environment.
        scheme (str): URL scheme, either 'http' or 'https' (default 'http')
        host(str): Hostname for the request (default 'falconframework.org')
        port (str or int, optional): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https').
        headers (dict or list, optional): Headers as a ``dict`` or an
            iterable collection of (*key*, *value*) ``tuple``'s
        app (str): Value for the ``SCRIPT_NAME`` environ variable, described in
            PEP-333: 'The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This may be an empty string, if the
            application corresponds to the "root" of the server.' (default '')
        body (str or unicode): The body of the request (default '')
        method (str): The HTTP method to use (default 'GET')
        wsgierrors (io): The stream to use as *wsgierrors*
            (default ``sys.stderr``)
        file_wrapper: Callable that returns an iterable, to be used as
            the value for *wsgi.file_wrapper* in the environ.

    """

    body = io.BytesIO(body.encode('utf-8')
                      if isinstance(body, six.text_type) else body)

    # NOTE(kgriffs): wsgiref, gunicorn, and uWSGI all unescape
    # the paths before setting PATH_INFO
    path = uri.decode(path)

    # NOTE(kgriffs): nocover since this branch will never be
    # taken in Python3. However, the branch is tested under Py2,
    # in test_utils.TestFalconTesting.test_unicode_path_in_create_environ
    if six.PY2 and isinstance(path, six.text_type):  # pragma: nocover
        path = path.encode('utf-8')

    scheme = scheme.lower()
    if port is None:
        port = '80' if scheme == 'http' else '443'
    else:
        port = str(port)

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
        'REMOTE_ADDR': '127.0.0.1',
        'SERVER_NAME': host,
        'SERVER_PORT': port,

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
        env['CONTENT_LENGTH'] = content_length

    if headers is not None:
        _add_headers_to_environ(env, headers)

    return env


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
