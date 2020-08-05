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

import asyncio
import cgi
from collections import defaultdict
import contextlib
import io
import itertools
import random
import socket
import sys
import time
from typing import Any, Dict

from falcon.constants import SINGLETON_HEADERS
import falcon.request
from falcon.util import http_now, uri

# Constants
DEFAULT_HOST = 'falconframework.org'

# NOTE(kgriffs): Alias for backwards-compatibility with Falcon 0.2
httpnow = http_now


class ASGILifespanEventEmitter:
    """Emits ASGI lifespan events to an ASGI app.

    This class can be used to drive a standard ASGI app callable in order to
    perform functional tests on the app in question.

    When simulating both lifespan and per-request events, each event stream
    will require a separate invocation of the ASGI callable; one with a
    lifespan event emitter, and one with a request event emitter. An
    asyncio :class:`~asyncio.Condition` can be used to pause the
    lifespan emitter until all of the desired request events have been
    emitted.

    Keyword Args:
        shutting_down (asyncio.Condition): An instance of
            :class:`asyncio.Condition` that will be awaited before
            emitting the final shutdown event (``'lifespan.shutdown``).
    """

    def __init__(self, shutting_down):
        self._state = 0
        self._shutting_down = shutting_down

    async def emit(self):
        if self._state == 0:
            self._state += 1
            return {'type': 'lifespan.startup'}

        if self._state == 1:
            self._state += 1
            # NOTE(kgriffs): This ensures the app ignores events it does
            #   not recognize.
            return {'type': 'lifespan._nonstandard_event'}

        async with self._shutting_down:
            await self._shutting_down.wait()

        return {'type': 'lifespan.shutdown'}

    __call__ = emit


class ASGIRequestEventEmitter:
    """Emits events on-demand to an ASGI app.

    This class can be used to drive a standard ASGI app callable in order to
    perform functional tests on the app in question.

    Note:
        In order to ensure the app is able to handle subtle variations
        in the ASGI events that are allowed by the specification, such
        variations are applied to the emitted events at unspecified
        intervals. This includes whether or not the `more_body` field
        is explicitly set, or whether or not the request `body` chunk in
        the event is occasionally empty,

    Keyword Args:
        body (str): The body content to use when emitting http.request
            events. May be an empty string. If a byte string, it will
            be used as-is; otherwise it will be encoded as UTF-8
            (default b'').
        disconnect_at (int): The Unix timestamp after which to begin
            returning http.disconnect events (default now + 30s).
        chunk_size (int): The maximum number of bytes to include in
            a single http.request event (default 4096).
    """

    # TODO(kgriffs): If this pattern later becomes useful elsewhere,
    #   factor out into a standalone helper class.
    _branch_decider = defaultdict(bool)  # type: defaultdict

    def __init__(self, body=None, disconnect_at=None, chunk_size=4096):
        if body is None:
            body = b''
        elif not isinstance(body, bytes):
            body = body.encode()

        if disconnect_at is None:
            disconnect_at = time.time() + 30

        self._body = body
        self._chunk_size = chunk_size
        self._disconnect_at = disconnect_at

        self._emitted_empty_chunk_a = False
        self._emitted_empty_chunk_b = False

    async def emit(self):
        if self._body is None:
            # NOTE(kgriffs): When there are no more events, an ASGI
            #   server will hang until the client connection
            #   disconnects.
            while time.time() < self._disconnect_at:
                await asyncio.sleep(1)

        if self._disconnect_at <= time.time():
            return {'type': 'http.disconnect'}

        event = {'type': 'http.request'}

        # NOTE(kgriffs): Return a couple variations on empty chunks
        #   every time, to ensure test coverage.
        if not self._emitted_empty_chunk_a:
            self._emitted_empty_chunk_a = True
            event['more_body'] = True
            return event

        if not self._emitted_empty_chunk_b:
            self._emitted_empty_chunk_b = True
            event['more_body'] = True
            event['body'] = b''
            return event

        # NOTE(kgriffs): Part of the time just return an
        #   empty chunk to make sure the app handles that
        #   correctly.
        if self._toggle_branch('return_empty_chunk'):
            event['more_body'] = True

            # NOTE(kgriffs): Since ASGI specifies that
            #   'body' is optional, we toggle whether
            #   or not to explicitly set it to b'' to ensure
            #   the app handles both correctly.
            if self._toggle_branch('explicit_empty_body_1'):
                event['body'] = b''

            return event

        chunk = self._body[:self._chunk_size]
        self._body = self._body[self._chunk_size:] or None

        if chunk:
            event['body'] = chunk
        elif self._toggle_branch('explicit_empty_body_2'):
            # NOTE(kgriffs): Since ASGI specifies that
            #   'body' is optional, we toggle whether
            #   or not to explicitly set it to b'' to ensure
            #   the app handles both correctly.
            event['body'] = b''

        if self._body:
            event['more_body'] = True
        elif self._toggle_branch('set_more_body_false'):
            # NOTE(kgriffs): The ASGI spec allows leaving off
            #   the 'more_body' key when it would be set to
            #   False, so toggle one of the approaches
            #   to make sure the app handles both cases.
            event['more_body'] = False

        return event

    __call__ = emit

    def _toggle_branch(self, name):
        self._branch_decider[name] = not self._branch_decider[name]
        return self._branch_decider[name]


class ASGIResponseEventCollector:
    """Collects and validates ASGI events returned by an app.

    Attributes:
        events (iterable): An iterable of events that were emitted by
            the app, collected as-is from the app.
        headers (iterable): An iterable of (str, str) tuples representing
            the UTF-8 decoded headers emitted by the app in the body of
            the ``'http.response.start'`` event.
        status (int): HTTP status code emitted by the app in the body of
            the ``'http.response.start'`` event.
        body_chunks (iterable): An iterable of ``bytes`` objects emitted
            by the app via ``'http.response.body'`` events.
        more_body (bool): Whether or not the app expects to emit more
            body chunks. Will be ``None`` if unknown (i.e., the app has
            not yet emitted any ``'http.response.body'`` events.)

    Raises:
        TypeError: An event field emitted by the app was of an unexpected type.
        ValueError: Invalid event name or field value.
    """

    _LIFESPAN_EVENT_TYPES = frozenset([
        'lifespan.startup.complete',
        'lifespan.startup.failed',
        'lifespan.shutdown.complete',
        'lifespan.shutdown.failed',
    ])

    def __init__(self):
        self.events = []
        self.headers = []
        self.status = None
        self.body_chunks = []
        self.more_body = None

    async def collect(self, event):
        if self.more_body is False:
            # NOTE(kgriffs): According to the ASGI spec, once we get a
            #   message setting more_body to False, any further messages
            #   on the channel are ignored.
            return

        self.events.append(event)

        event_type = event['type']
        if not isinstance(event_type, str):
            raise TypeError('ASGI event type must be a Unicode string')

        if event_type == 'http.response.start':
            for name, value in event.get('headers', []):
                if not isinstance(name, bytes):
                    raise TypeError('ASGI header names must be byte strings')
                if not isinstance(value, bytes):
                    raise TypeError('ASGI header names must be byte strings')

                name_decoded = name.decode()
                if not name_decoded.islower():
                    raise ValueError('ASGI header names must be lowercase')

                self.headers.append((name_decoded, value.decode()))

            self.status = event['status']

            if not isinstance(self.status, int):
                raise TypeError('ASGI status must be an int')

        elif event_type == 'http.response.body':
            chunk = event.get('body', b'')
            if not isinstance(chunk, bytes):
                raise TypeError('ASGI body content must be a byte string')

            self.body_chunks.append(chunk)

            self.more_body = event.get('more_body', False)
            if not isinstance(self.more_body, bool):
                raise TypeError('ASGI more_body flag must be a bool')

        elif event_type not in self._LIFESPAN_EVENT_TYPES:
            raise ValueError('Invalid ASGI event type: ' + event_type)

    __call__ = collect


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

    # NOTE(kgriffs): Added checks for text/event-stream and application/json
    if content_type in ('text/event-stream', 'application/json'):
        return 'UTF-8'

    if 'text' in content_type:
        return 'ISO-8859-1'

    return None


def get_unused_port() -> int:
    """Gets an unused localhost port for use by a test server.

    Warning:
        It is possible for a third party to bind to the returned port
        before the caller is able to do so. The caller will need to
        retry with a different port in that case.

    Warning:
        This method has only be tested on POSIX systems and may not
        work elsewhere.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


def rand_string(min, max) -> str:
    """Returns a randomly-generated string, of a random length.

    Args:
        min (int): Minimum string length to return, inclusive
        max (int): Maximum string length to return, inclusive

    """

    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord(' '), ord('~')))
                    for __ in range(string_length)])


def create_scope(path='/', query_string='', method='GET', headers=None,
                 host=DEFAULT_HOST, scheme=None, port=None, http_version='1.1',
                 remote_addr=None, root_path=None, content_length=None,
                 include_server=True) -> Dict[str, Any]:

    """Create a mock ASGI scope ``dict`` for simulating ASGI requests.

    Keyword Args:
        path (str): The path for the request (default '/')
        query_string (str): The query string to simulate, without a
            leading '?' (default ''). The query string is passed as-is
            (it will not be percent-encoded).
        method (str): The HTTP method to use (default 'GET')
        headers (dict): Headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). When the
            request will include a body, the Content-Length header should be
            included in this list. Header names are not case-sensitive.
        host(str): Hostname for the request (default 'falconframework.org').
            This also determines the the value of the Host header in the
            request.
        scheme (str): URL scheme, either 'http' or 'https' (default 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        remote_addr (str): Remote address for the request to use for
            the 'client' field in the connection scope (default None)
        root_path (str): The root path this application is mounted at; same as
            SCRIPT_NAME in WSGI (default '').
        content_length (int): The expected content length of the request
            body (default ``None``). If specified, this value will be
            used to set the Content-Length header in the request.
        include_server (bool): Set to ``False`` to not set the 'server' key
            in the scope ``dict`` (default ``True``).
    """

    http_version = _fixup_http_version(http_version)

    path = uri.decode(path, unquote_plus=False)

    # NOTE(kgriffs): Handles both None and ''
    query_string = query_string.encode() if query_string else b''

    if query_string and query_string.startswith(b'?'):
        raise ValueError("query_string should not start with '?'")

    scope = {
        'type': 'http',
        'asgi': {
            'version': '3.0',
            'spec_version': '2.1',
        },
        'http_version': http_version,
        'method': method.upper(),
        'path': path,
        'query_string': query_string,
    }

    # NOTE(kgriffs): Explicitly test against None so that the caller
    #   is able to simulate setting app to an empty string if they
    #   need to cover that branch in their code.
    if root_path is not None:
        # NOTE(kgriffs): Judging by the algorithm given in PEP-3333 for
        #   reconstructing the URL, SCRIPT_NAME is expected to contain a
        #   preceding slash character. Since ASGI states that this value is
        #   the same as WSGI's SCRIPT_NAME, we will follow suit here.
        if root_path and not root_path.startswith('/'):
            scope['root_path'] = '/' + root_path
        else:
            scope['root_path'] = root_path

    if scheme:
        if scheme not in ('http', 'https'):
            raise ValueError("scheme must be either 'http' or 'https'")

        scope['scheme'] = scheme

    if port is None:
        if (scheme or 'http') == 'http':
            port = 80
        else:
            port = 443
    else:
        port = int(port)

    if remote_addr:
        # NOTE(kgriffs): Choose from the standard IANA dynamic range
        remote_port = random.randint(49152, 65535)

        # NOTE(kgriffs): Expose as an iterable to ensure the framework/app
        #   isn't hard-coded to only work with a list or tuple.
        scope['client'] = iter([remote_addr, remote_port])

    if include_server:
        scope['server'] = iter([host, port])

    _add_headers_to_scope(scope, headers, content_length, host, port, scheme, http_version)

    return scope


def create_environ(path='/', query_string='', http_version='1.1',
                   scheme='http', host=DEFAULT_HOST, port=None,
                   headers=None, app=None, body='', method='GET',
                   wsgierrors=None, file_wrapper=None, remote_addr=None,
                   root_path=None, cookies=None) -> Dict[str, Any]:

    """Creates a mock PEP-3333 environ ``dict`` for simulating WSGI requests.

    Keyword Args:
        path (str): The path for the request (default '/')
        query_string (str): The query string to simulate, without a
            leading '?' (default ''). The query string is passed as-is
            (it will not be percent-encoded).
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        scheme (str): URL scheme, either 'http' or 'https' (default 'http')
        host(str): Hostname for the request (default 'falconframework.org')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        headers (dict): Headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        root_path (str): Value for the ``SCRIPT_NAME`` environ variable, described in
            PEP-333: 'The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This may be an empty string, if the
            application corresponds to the "root" of the server.' (default '')
        app (str): Deprecated alias for `root_path`. If both kwargs are passed,
            `root_path` takes precedence.
        body (str): The body of the request (default ''). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        method (str): The HTTP method to use (default 'GET')
        wsgierrors (io): The stream to use as *wsgierrors*
            (default ``sys.stderr``)
        file_wrapper: Callable that returns an iterable, to be used as
            the value for *wsgi.file_wrapper* in the environ.
        remote_addr (str): Remote address for the request to use as the
            'REMOTE_ADDR' environ variable (default None)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    """

    http_version = _fixup_http_version(http_version)

    if query_string and query_string.startswith('?'):
        raise ValueError("query_string should not start with '?'")

    body = io.BytesIO(body.encode('utf-8')
                      if isinstance(body, str) else body)

    # NOTE(kgriffs): wsgiref, gunicorn, and uWSGI all unescape
    # the paths before setting PATH_INFO
    path = uri.decode(path, unquote_plus=False)

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

    scheme = scheme.lower()
    if port is None:
        port = '80' if scheme == 'http' else '443'
    else:
        # NOTE(kgriffs): Running it through int() first ensures that if
        #   a string was passed, it is a valid integer.
        port = str(int(port))

    root_path = root_path or app or ''

    # NOTE(kgriffs): Judging by the algorithm given in PEP-3333 for
    # reconstructing the URL, SCRIPT_NAME is expected to contain a
    # preceding slash character.
    if root_path and not root_path.startswith('/'):
        root_path = '/' + root_path

    env = {
        'SERVER_PROTOCOL': 'HTTP/' + http_version,
        'SERVER_SOFTWARE': 'gunicorn/0.17.0',
        'SCRIPT_NAME': (root_path or ''),
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'REMOTE_PORT': '65133',
        'RAW_URI': '/',
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

    # NOTE(kgriffs): It has been observed that WSGI servers do not always
    #   set the REMOTE_ADDR variable, so we don't always set it either, to
    #   ensure the framework/app handles that case correctly.
    if remote_addr:
        env['REMOTE_ADDR'] = remote_addr

    if file_wrapper is not None:
        env['wsgi.file_wrapper'] = file_wrapper

    if http_version != '1.0':
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

    # NOTE(myuz): Clients discard Set-Cookie header
    #  in the response to the OPTIONS method.
    if cookies is not None and method != 'OPTIONS':
        cookies = [
            '{}={}'.format(key, cookie.value if hasattr(cookie, 'value') else cookie)
            for key, cookie in cookies.items()
        ]
        env['HTTP_COOKIE'] = '; '.join(cookies)

    if headers is not None:
        _add_headers_to_environ(env, headers)

    return env


def create_req(options=None, **kwargs) -> falcon.Request:
    """Create and return a new Request instance.

    This function can be used to conveniently create a WSGI environ
    and use it to instantiate a :py:class:`falcon.Request` object in one go.

    The arguments for this function are identical to those
    of :py:meth:`falcon.testing.create_environ`, except an additional
    `options` keyword argument may be set to an instance of
    :py:class:`falcon.RequestOptions` to configure certain
    aspects of request parsing in lieu of the defaults.
    """

    env = create_environ(**kwargs)
    return falcon.request.Request(env, options=options)


def create_asgi_req(body=None, req_type=None, options=None, **kwargs) -> falcon.Request:
    """Create and return a new ASGI Request instance.

    This function can be used to conveniently create an ASGI scope
    and use it to instantiate a :py:class:`falcon.asgi.Request` object
    in one go.

    The arguments for this function are identical to those
    of :py:meth:`falcon.testing.create_environ`, with the addition of
    `body`, `req_type`, and `options` arguments as documented below.

    Keyword Arguments:
        body (bytes): The body data to use for the request (default b''). If
            the value is a :py:class:`str`, it will be UTF-8 encoded to
            a byte string.
        req_type (object): A subclass of :py:class:`falcon.asgi.Request`
            to instantiate. If not specified, the standard
            :py:class:`falcon.asgi.Request` class will simply be used.
        options (falcon.RequestOptions): An instance of
            :py:class:`falcon.RequestOptions` that should be used to determine
            certain aspects of request parsing in lieu of the defaults.
    """

    scope = create_scope(**kwargs)

    body = body or b''
    disconnect_at = time.time() + 300

    req_event_emitter = ASGIRequestEventEmitter(body, disconnect_at)

    # NOTE(kgriffs): Import here in case the app is running under
    #   Python 3.5 (in which case as long as it does not call the
    #   present function, it won't trigger an import error).
    import falcon.asgi

    req_type = req_type or falcon.asgi.Request
    return req_type(scope, req_event_emitter, options=options)


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
    exception or exhausting iteration.

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
    try:
        items = headers.items()
    except AttributeError:
        items = headers

    for name, value in items:
        name_wsgi = name.upper().replace('-', '_')
        if name_wsgi not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            name_wsgi = 'HTTP_' + name_wsgi

        if value is None:
            value = ''
        else:
            value = value.strip()

        if name_wsgi not in env or name.lower() in SINGLETON_HEADERS:
            env[name_wsgi] = value
        else:
            env[name_wsgi] += ',' + value


def _add_headers_to_scope(scope, headers, content_length, host, port, scheme, http_version):
    if headers:
        try:
            items = headers.items()
        except AttributeError:
            items = headers

        prepared_headers = [
            # NOTE(kgriffs): Expose as an iterable to ensure the framework/app
            #   isn't hard-coded to only work with a list or tuple.
            # NOTE(kgriffs): Value is stripped if not empty, otherwise defaults
            #   to b'' to be consistent with _add_headers_to_environ().
            iter([name.lower().encode(), value.strip().encode() if value else b''])

            # NOTE(kgriffs): Use tuple unpacking to support iterables
            #   that yield arbitary two-item iterable objects.
            for name, value in items
        ]
    else:
        prepared_headers = []

    if content_length is not None:
        value = str(content_length).encode()
        prepared_headers.append((b'content-length', value))

    if http_version != '1.0':
        host_header = host

        if scheme == 'https':
            if port != 443:
                host_header += ':' + str(port)
        else:
            if port != 80:
                host_header += ':' + str(port)

        prepared_headers.append([b'host', host_header.encode()])

    # NOTE(kgriffs): Make it an iterator to ensure the app is not expecting
    #   a specific type (ASGI only specified that it is an iterable).
    scope['headers'] = iter(prepared_headers)


def _fixup_http_version(http_version) -> str:
    if http_version not in ('2', '2.0', '1.1', '1.0', '1'):
        raise ValueError('Invalid http_version specified: ' + http_version)

    # NOTE(kgrifs): Normalize so that they conform to the standard
    #   protocol names with prefixed with "HTTP/"
    if http_version == '2.0':
        http_version = '2'
    elif http_version == '1':
        http_version = '1.0'

    return http_version
