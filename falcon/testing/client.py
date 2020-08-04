# Copyright 2016 by Rackspace Hosting, Inc.
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

"""WSGI test client utilities.

This package includes utilities for simulating HTTP requests against a
WSGI callable, without having to stand up a WSGI server.
"""

import asyncio
import datetime as dt
import inspect
import time
from typing import Dict, Optional, Union
import warnings
import wsgiref.validate

from falcon.constants import COMBINED_METHODS, MEDIA_JSON
from falcon.testing import helpers
from falcon.testing.srmock import StartResponseMock
from falcon.util import (
    CaseInsensitiveDict,
    code_to_http_status,
    get_loop,
    http_cookies,
    http_date_to_dt,
    invoke_coroutine_sync,
    json as util_json,
    to_query_str,
)

warnings.filterwarnings(
    'error',
    (
        'Unknown REQUEST_METHOD: ' +
        "'({})'".format(
            '|'.join(COMBINED_METHODS)
        )
    ),
    wsgiref.validate.WSGIWarning,
    '',
    0,
)


class Cookie:
    """Represents a cookie returned by a simulated request.

    Args:
        morsel: A ``Morsel`` object from which to derive the cookie
            data.

    Attributes:
        name (str): The cookie's name.
        value (str): The value of the cookie.
        expires(datetime.datetime): Expiration timestamp for the cookie,
            or ``None`` if not specified.
        path (str): The path prefix to which this cookie is restricted,
            or ``None`` if not specified.
        domain (str): The domain to which this cookie is restricted,
            or ``None`` if not specified.
        max_age (int): The lifetime of the cookie in seconds, or
            ``None`` if not specified.
        secure (bool): Whether or not the cookie may only only be
            transmitted from the client via HTTPS.
        http_only (bool): Whether or not the cookie may only be
            included in unscripted requests from the client.
    """

    def __init__(self, morsel):
        self._name = morsel.key
        self._value = morsel.value

        for name in (
            'expires',
            'path',
            'domain',
            'max_age',
            'secure',
            'httponly',
            'samesite'
        ):
            value = morsel[name.replace('_', '-')] or None
            setattr(self, '_' + name, value)

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value

    @property
    def expires(self) -> Optional[dt.datetime]:
        if self._expires:  # type: ignore[attr-defined]
            return http_date_to_dt(self._expires, obs_date=True)  # type: ignore[attr-defined]

        return None

    @property
    def path(self) -> str:
        return self._path  # type: ignore[attr-defined]

    @property
    def domain(self) -> str:
        return self._domain  # type: ignore[attr-defined]

    @property
    def max_age(self) -> Optional[int]:
        return int(self._max_age) if self._max_age else None  # type: ignore[attr-defined]

    @property
    def secure(self) -> bool:
        return bool(self._secure)  # type: ignore[attr-defined]

    @property
    def http_only(self) -> bool:
        return bool(self._httponly)  # type: ignore[attr-defined]

    @property
    def same_site(self) -> Optional[int]:
        return self._samesite if self._samesite else None  # type: ignore[attr-defined]


class Result:
    """Encapsulates the result of a simulated request.

    Args:
        iterable (iterable): An iterable that yields zero or more
            bytestrings, per PEP-3333
        status (str): An HTTP status string, including status code and
            reason string
        headers (list): A list of (header_name, header_value) tuples,
            per PEP-3333

    Attributes:
        status (str): HTTP status string given in the response
        status_code (int): The code portion of the HTTP status string
        headers (CaseInsensitiveDict): A case-insensitive dictionary
            containing all the headers in the response, except for
            cookies, which may be accessed via the `cookies`
            attribute.

            Note:

                Multiple instances of a header in the response are
                currently not supported; it is unspecified which value
                will "win" and be represented in `headers`.

        cookies (dict): A dictionary of
            :py:class:`falcon.testing.Cookie` values parsed from the
            response, by name.

            The cookies dictionary can be used directly in subsequent requests::

                client = testing.TestClient(app)
                response_one = client.simulate_get('/')
                response_two = client.simulate_post('/', cookies=response_one.cookies)

        encoding (str): Text encoding of the response body, or ``None``
            if the encoding can not be determined.
        content (bytes): Raw response body, or ``bytes`` if the
            response body was empty.
        text (str): Decoded response body of type ``str``.
            If the content type does not specify an encoding, UTF-8 is
            assumed.
        json (JSON serializable): Deserialized JSON body. Will be ``None`` if
            the body has no content to deserialize. Otherwise, raises an error
            if the response is not valid JSON.
    """

    def __init__(self, iterable, status, headers, events=None):
        self._text = None

        self._content = b''.join(iterable)

        self._status = status
        self._status_code = int(status[:3])
        self._headers = CaseInsensitiveDict(headers)
        self._events = events or []

        cookies = http_cookies.SimpleCookie()
        for name, value in headers:
            if name.lower() == 'set-cookie':
                cookies.load(value)

        self._cookies = dict(
            (morsel.key, Cookie(morsel))
            for morsel in cookies.values()
        )

        self._encoding = helpers.get_encoding_from_headers(self._headers)

    @property
    def status(self) -> str:
        return self._status

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> CaseInsensitiveDict:
        # NOTE(kgriffs): It would probably be better to annotate this with
        #   a generic Mapping[str, str] type, but currently there is an
        #   incompatibility with Cython that prevents us from modifying
        #   CaseInsensitiveDict to inherit from a generic MutableMapping
        #   type. This might be resolved in the future by moving
        #   the CaseInsensitiveDict implementation to the falcon.testing
        #   module so that it is no longer cythonized.
        return self._headers

    @property
    def cookies(self) -> Dict[str, Cookie]:
        return self._cookies

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        if self._text is None:
            if not self.content:
                self._text = ''
            else:
                if self.encoding is None:
                    encoding = 'UTF-8'
                else:
                    encoding = self.encoding

                self._text = self.content.decode(encoding)

        return self._text

    @property
    def json(self) -> Optional[Union[dict, list, str, int, float, bool]]:
        if not self.text:
            return None

        return util_json.loads(self.text)


# NOTE(kgriffs): The default of asgi_disconnect_ttl was chosen to be
#   relatively long (5 minutes) to help testers notice when something
#   appears to be "hanging", which might indicates that the app is
#   not handling the reception of events correctly.
def simulate_request(app, method='GET', path='/', query_string=None,
                     headers=None, content_type=None, body=None, json=None,
                     file_wrapper=None, wsgierrors=None, params=None,
                     params_csv=False, protocol='http', host=helpers.DEFAULT_HOST,
                     remote_addr=None, extras=None, http_version='1.1',
                     port=None, root_path=None, cookies=None, asgi_chunk_size=4096,
                     asgi_disconnect_ttl=300) -> Result:

    """Simulates a request to a WSGI or ASGI application.

    Performs a request against a WSGI or ASGI application. In the case of
    WSGI, uses :any:`wsgiref.validate` to ensure the response is valid.

    Keyword Args:
        app (callable): The WSGI or ASGI application to call
        method (str): An HTTP method to use in the request
            (default: 'GET')
        path (str): The URL path to request (default: '/').

            Note:
                The path may contain a query string. However, neither
                `query_string` nor `params` may be specified in this case.

        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        content_type (str): The value to use for the Content-Type header in
            the request. If specified, this value will take precedence over
            any value set for the Content-Type header in the
            `headers` keyword argument. The ``falcon`` module provides a number
            of :ref:`constants for common media types <media_type_constants>`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        body (str): The body of the request (default ''). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and sets the Content-Type header to
            ``'application/json'``, overriding any value specified by either
            the `content_type` or `headers` arguments.
        file_wrapper (callable): Callable that returns an iterable,
            to be used as the value for *wsgi.file_wrapper* in the
            WSGI environ (default: ``None``). This can be used to test
            high-performance file transmission when `resp.stream` is
            set to a file-like object.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """

    if not path.startswith('/'):
        raise ValueError("path must start with '/'")

    if '?' in path:
        if query_string or params:
            raise ValueError(
                'path may not contain a query string in combination with '
                'the query_string or params parameters. Please use only one '
                'way of specifying the query string.'
            )
        path, query_string = path.split('?', 1)
    elif query_string and query_string.startswith('?'):
        raise ValueError("query_string should not start with '?'")

    extras = extras or {}

    if query_string is None:
        query_string = to_query_str(
            params,
            comma_delimited_lists=params_csv,
            prefix=False,
        )

    if content_type is not None:
        headers = headers or {}
        headers['Content-Type'] = content_type

    if json is not None:
        body = util_json.dumps(json, ensure_ascii=False)
        headers = headers or {}
        headers['Content-Type'] = MEDIA_JSON

    if not _is_asgi_app(app):
        env = helpers.create_environ(
            method=method,
            scheme=protocol,
            path=path,
            query_string=(query_string or ''),
            headers=headers,
            body=body,
            file_wrapper=file_wrapper,
            host=host,
            remote_addr=remote_addr,
            wsgierrors=wsgierrors,
            http_version=http_version,
            port=port,
            root_path=root_path,
            cookies=cookies,
        )

        if 'REQUEST_METHOD' in extras and extras['REQUEST_METHOD'] != method:
            # NOTE(vytas): Even given the duct tape nature of overriding
            # arbitrary environ variables, changing the method can potentially
            # be very confusing, particularly when using specialized
            # simulate_get/post/patch etc methods.
            raise ValueError(
                'WSGI environ extras may not override the request method. '
                'Please use the method parameter.'
            )

        env.update(extras)

        srmock = StartResponseMock()
        validator = wsgiref.validate.validator(app)

        iterable = validator(env, srmock)

        return Result(helpers.closed_wsgi_iterable(iterable),
                      srmock.status, srmock.headers)

    # ---------------------------------------------------------------------
    # NOTE(kgriffs): 'lifespan' scope
    # ---------------------------------------------------------------------

    lifespan_scope = {
        'type': 'lifespan',
        'asgi': {
            'version': '3.0',
            'spec_version': '2.0',
        },
    }

    shutting_down = asyncio.Condition()
    lifespan_event_emitter = helpers.ASGILifespanEventEmitter(shutting_down)
    lifespan_event_collector = helpers.ASGIResponseEventCollector()

    # ---------------------------------------------------------------------
    # NOTE(kgriffs): 'http' scope
    # ---------------------------------------------------------------------

    content_length = None

    if body is not None:
        if isinstance(body, str):
            body = body.encode()

        content_length = len(body)

    http_scope = helpers.create_scope(
        path=path,
        query_string=query_string,
        method=method,
        headers=headers,
        host=host,
        scheme=protocol,
        port=port,
        http_version=http_version,
        remote_addr=remote_addr,
        root_path=root_path,
        content_length=content_length,
    )

    if 'method' in extras and extras['method'] != method.upper():
        raise ValueError(
            'ASGI scope extras may not override the request method. '
            'Please use the method parameter.'
        )

    http_scope.update(extras)

    disconnect_at = time.time() + max(0, asgi_disconnect_ttl)
    req_event_emitter = helpers.ASGIRequestEventEmitter(
        (body or b''),
        disconnect_at,
        chunk_size=asgi_chunk_size
    )

    resp_event_collector = helpers.ASGIResponseEventCollector()

    async def conductor():
        # NOTE(kgriffs): We assume this is a Falcon ASGI app, which supports
        #   the lifespan protocol and thus we do not need to catch
        #   exceptions that would signify no lifespan protocol support.
        t = get_loop().create_task(
            app(lifespan_scope, lifespan_event_emitter, lifespan_event_collector)
        )

        await _wait_for_startup(lifespan_event_collector.events)

        await app(http_scope, req_event_emitter, resp_event_collector)

        # NOTE(kgriffs): Notify lifespan_event_emitter that it is OK
        #   to proceed.
        async with shutting_down:
            shutting_down.notify()

        await _wait_for_shutdown(lifespan_event_collector.events)
        await t

    invoke_coroutine_sync(conductor)

    return Result(resp_event_collector.body_chunks,
                  code_to_http_status(resp_event_collector.status),
                  resp_event_collector.headers,
                  events=resp_event_collector.events)


def simulate_get(app, path, **kwargs) -> Result:
    """Simulates a GET request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'GET', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

            Note:
                The path may contain a query string. However, neither
                `query_string` nor `params` may be specified in this case.

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        file_wrapper (callable): Callable that returns an iterable,
            to be used as the value for *wsgi.file_wrapper* in the
            WSGI environ (default: ``None``). This can be used to test
            high-performance file transmission when `resp.stream` is
            set to a file-like object.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """

    return simulate_request(app, 'GET', path, **kwargs)


def simulate_head(app, path, **kwargs) -> Result:
    """Simulates a HEAD request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'HEAD', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

            Note:
                The path may contain a query string. However, neither
                `query_string` nor `params` may be specified in this case.

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """
    return simulate_request(app, 'HEAD', path, **kwargs)


def simulate_post(app, path, **kwargs) -> Result:
    """Simulates a POST request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'POST', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        content_type (str): The value to use for the Content-Type header in
            the request. If specified, this value will take precedence over
            any value set for the Content-Type header in the
            `headers` keyword argument. The ``falcon`` module provides a number
            of :ref:`constants for common media types <media_type_constants>`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        body (str): The body of the request (default ''). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and sets the Content-Type header to
            ``'application/json'``, overriding any value specified by either
            the `content_type` or `headers` arguments.
        file_wrapper (callable): Callable that returns an iterable,
            to be used as the value for *wsgi.file_wrapper* in the
            WSGI environ (default: ``None``). This can be used to test
            high-performance file transmission when `resp.stream` is
            set to a file-like object.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """
    return simulate_request(app, 'POST', path, **kwargs)


def simulate_put(app, path, **kwargs) -> Result:
    """Simulates a PUT request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'PUT', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        content_type (str): The value to use for the Content-Type header in
            the request. If specified, this value will take precedence over
            any value set for the Content-Type header in the
            `headers` keyword argument. The ``falcon`` module provides a number
            of :ref:`constants for common media types <media_type_constants>`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        body (str): The body of the request (default ''). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and sets the Content-Type header to
            ``'application/json'``, overriding any value specified by either
            the `content_type` or `headers` arguments.
        file_wrapper (callable): Callable that returns an iterable,
            to be used as the value for *wsgi.file_wrapper* in the
            WSGI environ (default: ``None``). This can be used to test
            high-performance file transmission when `resp.stream` is
            set to a file-like object.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """
    return simulate_request(app, 'PUT', path, **kwargs)


def simulate_options(app, path, **kwargs) -> Result:
    """Simulates an OPTIONS request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'OPTIONS', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)

    Returns:
        :py:class:`~.Result`: The result of the request
    """
    return simulate_request(app, 'OPTIONS', path, **kwargs)


def simulate_patch(app, path, **kwargs) -> Result:
    """Simulates a PATCH request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'PATCH', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        content_type (str): The value to use for the Content-Type header in
            the request. If specified, this value will take precedence over
            any value set for the Content-Type header in the
            `headers` keyword argument. The ``falcon`` module provides a number
            of :ref:`constants for common media types <media_type_constants>`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        body (str): The body of the request (default ''). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and sets the Content-Type header to
            ``'application/json'``, overriding any value specified by either
            the `content_type` or `headers` arguments.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """
    return simulate_request(app, 'PATCH', path, **kwargs)


def simulate_delete(app, path, **kwargs) -> Result:
    """Simulates a DELETE request to a WSGI or ASGI application.

    Equivalent to::

         simulate_request(app, 'DELETE', path, **kwargs)

    Args:
        app (callable): The application to call
        path (str): The URL path to request

    Keyword Args:
        root_path (str): The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This defaults to the empty string,
            indicating that the application corresponds to the "root" of the
            server.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        port (int): The TCP port to simulate. Defaults to
            the standard port used by the given scheme (i.e., 80 for 'http'
            and 443 for 'https'). A string may also be passed, as long as
            it can be parsed as an int.
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``True`` to encode list values
            in query string params as comma-separated values
            (e.g., 'thing=1,2,3'). Otherwise, parameters will be encoded by
            specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Defaults to ``False``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        content_type (str): The value to use for the Content-Type header in
            the request. If specified, this value will take precedence over
            any value set for the Content-Type header in the
            `headers` keyword argument. The ``falcon`` module provides a number
            of :ref:`constants for common media types <media_type_constants>`.
        headers (dict): Extra headers as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of strings provides the name and value
            for an HTTP header. If desired, multiple header values may be
            combined into a single (*name*, *value*) pair by joining the values
            with a comma when the header in question supports the list
            format (see also RFC 7230 and RFC 7231). Header names are not
            case-sensitive.
        body (str): The body of the request (default ''). The value will be
            encoded as UTF-8 in the WSGI environ. Alternatively, a byte string
            may be passed, in which case it will be used as-is.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and sets the Content-Type header to
            ``'application/json'``, overriding any value specified by either
            the `content_type` or `headers` arguments.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1'). For WSGI, this corresponds to
            the 'REMOTE_ADDR' environ variable. For ASGI, this corresponds
            to the IP address used for the 'client' field in the connection
            scope.
        http_version (str): The HTTP version to simulate. Must be either
            '2', '2.0', 1.1', '1.0', or '1' (default '1.1'). If set to '1.0',
            the Host header will not be added to the scope.
        wsgierrors (io): The stream to use as *wsgierrors* in the WSGI
            environ (default ``sys.stderr``)
        asgi_chunk_size (int): The maximum number of bytes that will be
            sent to the ASGI app in a single 'http.request' event (default
            4096).
        asgi_disconnect_ttl (int): The maximum number of seconds to wait
            since the request was initiated, before emitting an
            'http.disconnect' event when the app calls the
            receive() function (default 300).
        extras (dict): Additional values to add to the WSGI
            ``environ`` dictionary or the ASGI scope for the request
            (default: ``None``)
        cookies (dict): Cookies as a dict-like (Mapping) object, or an
            iterable yielding a series of two-member (*name*, *value*)
            iterables. Each pair of items provides the name and value
            for the 'Set-Cookie' header.

    Returns:
        :py:class:`~.Result`: The result of the request
    """
    return simulate_request(app, 'DELETE', path, **kwargs)


class TestClient:
    """Simulates requests to a WSGI or ASGI application.

    This class provides a contextual wrapper for Falcon's `simulate_*`
    test functions. It lets you replace this::

        simulate_get(app, '/messages')
        simulate_head(app, '/messages')

    with this::

        client = TestClient(app)
        client.simulate_get('/messages')
        client.simulate_head('/messages')

    Note:
        The methods all call ``self.simulate_request()`` for convenient
        overriding of request preparation by child classes.

    Args:
        app (callable): A WSGI or ASGI application to target when simulating
            requests

    Keyword Arguments:
        headers (dict): Default headers to set on every request (default
            ``None``). These defaults may be overridden by passing values
            for the same headers to one of the `simulate_*()` methods.

    Attributes:
        app: The app that this client instance was configured to use.

    """

    def __init__(self, app, headers=None):
        self.app = app
        self._default_headers = headers

    def simulate_get(self, path='/', **kwargs) -> Result:
        """Simulates a GET request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_get`)
        """
        return self.simulate_request('GET', path, **kwargs)

    def simulate_head(self, path='/', **kwargs) -> Result:
        """Simulates a HEAD request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_head`)
        """
        return self.simulate_request('HEAD', path, **kwargs)

    def simulate_post(self, path='/', **kwargs) -> Result:
        """Simulates a POST request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_post`)
        """
        return self.simulate_request('POST', path, **kwargs)

    def simulate_put(self, path='/', **kwargs) -> Result:
        """Simulates a PUT request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_put`)
        """
        return self.simulate_request('PUT', path, **kwargs)

    def simulate_options(self, path='/', **kwargs) -> Result:
        """Simulates an OPTIONS request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_options`)
        """
        return self.simulate_request('OPTIONS', path, **kwargs)

    def simulate_patch(self, path='/', **kwargs) -> Result:
        """Simulates a PATCH request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_patch`)
        """
        return self.simulate_request('PATCH', path, **kwargs)

    def simulate_delete(self, path='/', **kwargs) -> Result:
        """Simulates a DELETE request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_delete`)
        """
        return self.simulate_request('DELETE', path, **kwargs)

    def simulate_request(self, *args, **kwargs) -> Result:
        """Simulates a request to a WSGI application.

        Wraps :py:meth:`falcon.testing.simulate_request` to perform a
        WSGI request directly against ``self.app``. Equivalent to::

            falcon.testing.simulate_request(self.app, *args, **kwargs)
        """

        if self._default_headers:
            # NOTE(kgriffs): Handle the case in which headers is explicitly
            # set to None.
            additional_headers = kwargs.get('headers', {}) or {}

            merged_headers = self._default_headers.copy()
            merged_headers.update(additional_headers)

            kwargs['headers'] = merged_headers

        return simulate_request(self.app, *args, **kwargs)


# -----------------------------------------------------------------------------
# Private
# -----------------------------------------------------------------------------


def _is_asgi_app(app):
    app_args = inspect.getfullargspec(app).args
    num_app_args = len(app_args)

    # NOTE(kgriffs): Technically someone could name the "self" or "cls"
    #   arg something else, but we will make the simplifying
    #   assumption that this is rare enough to not worry about.
    if app_args[0] in {'cls', 'self'}:
        num_app_args -= 1

    is_asgi = (num_app_args == 3)

    return is_asgi


async def _wait_for_startup(events):
    # NOTE(kgriffs): This is covered, but our gate for some reason doesn't
    #   understand `while True`.
    while True:  # pragma: nocover
        for e in events:
            if e['type'] == 'lifespan.startup.failed':
                raise RuntimeError('ASGI app returned lifespan.startup.failed. ' + e['message'])

        if any(e['type'] == 'lifespan.startup.complete' for e in events):
            break

        # NOTE(kgriffs): Yield to the concurrent lifespan task
        await asyncio.sleep(0.001)


async def _wait_for_shutdown(events):
    # NOTE(kgriffs): This is covered, but our gate for some reason doesn't
    #   understand `while True`.
    while True:  # pragma: nocover
        for e in events:
            if e['type'] == 'lifespan.shutdown.failed':
                raise RuntimeError('ASGI app returned lifespan.shutdown.failed. ' + e['message'])

        if any(e['type'] == 'lifespan.shutdown.complete' for e in events):
            break

        # NOTE(kgriffs): Yield to the concurrent lifespan task
        await asyncio.sleep(0.001)
