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

import warnings
import wsgiref.validate

from falcon.constants import MEDIA_JSON
from falcon.testing import helpers
from falcon.testing.srmock import StartResponseMock
from falcon.util import CaseInsensitiveDict, compat, http_date_to_dt, to_query_str
from falcon.util import json as util_json
from falcon.util.compat import http_cookies


warnings.filterwarnings(
    'ignore',
    (
        'Unknown REQUEST_METHOD: '
        "'(CONNECT|CHECKIN|CHECKOUT|UNCHECKIN|UPDATE|VERSION-CONTROL|REPORT|SETECASTRONOMY)'"
    ),
    wsgiref.validate.WSGIWarning,
    '',
    0,
)


class Result(object):
    """Encapsulates the result of a simulated WSGI request.

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
        encoding (str): Text encoding of the response body, or ``None``
            if the encoding can not be determined.
        content (bytes): Raw response body, or ``bytes`` if the
            response body was empty.
        text (str): Decoded response body of type ``unicode``
            under Python 2.7, and of type ``str`` otherwise.
            If the content type does not specify an encoding, UTF-8 is
            assumed.
        json (JSON serializable): Deserialized JSON body. Will be ``None`` if
            the body has no content to deserialize. Otherwise, raises an error
            if the response is not valid JSON.
    """

    def __init__(self, iterable, status, headers):
        self._text = None

        self._content = b''.join(iterable)

        self._status = status
        self._status_code = int(status[:3])
        self._headers = CaseInsensitiveDict(headers)

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
    def status(self):
        return self._status

    @property
    def status_code(self):
        return self._status_code

    @property
    def headers(self):
        return self._headers

    @property
    def cookies(self):
        return self._cookies

    @property
    def encoding(self):
        return self._encoding

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        if self._text is None:
            if not self.content:
                self._text = u''
            else:
                if self.encoding is None:
                    encoding = 'UTF-8'
                else:
                    encoding = self.encoding

                self._text = self.content.decode(encoding)

        return self._text

    @property
    def json(self):
        if not self.text:
            return None

        return util_json.loads(self.text)


class Cookie(object):
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
        ):
            value = morsel[name.replace('_', '-')] or None
            setattr(self, '_' + name, value)

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def expires(self):
        if self._expires:
            return http_date_to_dt(self._expires, obs_date=True)

        return None

    @property
    def path(self):
        return self._path

    @property
    def domain(self):
        return self._domain

    @property
    def max_age(self):
        return int(self._max_age) if self._max_age else None

    @property
    def secure(self):
        return bool(self._secure)

    @property
    def http_only(self):
        return bool(self._httponly)


def simulate_request(app, method='GET', path='/', query_string=None,
                     headers=None, body=None, json=None, file_wrapper=None,
                     wsgierrors=None, params=None, params_csv=True,
                     protocol='http', host=helpers.DEFAULT_HOST,
                     remote_addr=None, extras=None):
    """Simulates a request to a WSGI application.

    Performs a request against a WSGI application. Uses
    :any:`wsgiref.validate` to ensure the response is valid
    WSGI.

    Keyword Args:
        app (callable): The WSGI application to call
        method (str): An HTTP method to use in the request
            (default: 'GET')
        path (str): The URL path to request (default: '/').

            Note:
                The path may contain a query string. However, neither
                `query_string` nor `params` may be specified in this case.

        protocol: The protocol to use for the URL scheme
            (default: 'http')
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        body (str): A string to send as the body of the request.
            Accepts both byte strings and Unicode strings
            (default: ``None``). If a Unicode string is provided,
            it will be encoded as UTF-8 in the request.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and the Content-Type header in
            `headers`.
        file_wrapper (callable): Callable that returns an iterable,
            to be used as the value for *wsgi.file_wrapper* in the
            environ (default: ``None``). This can be used to test
            high-performance file transmission when `resp.stream` is
            set to a file-like object.
        host(str): A string to use for the hostname part of the fully
            qualified request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        wsgierrors (io): The stream to use as *wsgierrors*
            (default ``sys.stderr``)
        extras (dict): Additional CGI variables to add to the WSGI
            ``environ`` dictionary for the request (default: ``None``)

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
    if 'REQUEST_METHOD' in extras and extras['REQUEST_METHOD'] != method:
        # NOTE(vytas): Even given the duct tape nature of overriding
        # arbitrary environ variables, changing the method can potentially
        # be very confusing, particularly when using specialized
        # simulate_get/post/patch etc methods.
        raise ValueError(
            'environ extras may not override the request method. Please '
            'use the method parameter.'
        )

    if query_string is None:
        query_string = to_query_str(
            params,
            comma_delimited_lists=params_csv,
            prefix=False,
        )

    if json is not None:
        body = util_json.dumps(json, ensure_ascii=False)
        headers = headers or {}
        headers['Content-Type'] = MEDIA_JSON

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
    )
    if extras:
        env.update(extras)

    srmock = StartResponseMock()
    validator = wsgiref.validate.validator(app)

    iterable = validator(env, srmock)

    result = Result(helpers.closed_wsgi_iterable(iterable),
                    srmock.status, srmock.headers)

    return result


def simulate_get(app, path, **kwargs):
    """Simulates a GET request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'GET', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request.

            Note:
                The path may contain a query string. However, neither
                `query_string` nor `params` may be specified in this case.

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        file_wrapper (callable): Callable that returns an iterable,
            to be used as the value for *wsgi.file_wrapper* in the
            environ (default: ``None``). This can be used to test
            high-performance file transmission when `resp.stream` is
            set to a file-like object.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'GET', path, **kwargs)


def simulate_head(app, path, **kwargs):
    """Simulates a HEAD request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'HEAD', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request.

            Note:
                The path may contain a query string. However, neither
                `query_string` nor `params` may be specified in this case.

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        query_string (str): A raw query string to include in the
            request (default: ``None``). If specified, overrides
            `params`.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'HEAD', path, **kwargs)


def simulate_post(app, path, **kwargs):
    """Simulates a POST request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'POST', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        body (str): A string to send as the body of the request.
            Accepts both byte strings and Unicode strings
            (default: ``None``). If a Unicode string is provided,
            it will be encoded as UTF-8 in the request.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and the Content-Type header in
            `headers`.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'POST', path, **kwargs)


def simulate_put(app, path, **kwargs):
    """Simulates a PUT request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'PUT', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        body (str): A string to send as the body of the request.
            Accepts both byte strings and Unicode strings
            (default: ``None``). If a Unicode string is provided,
            it will be encoded as UTF-8 in the request.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and the Content-Type header in
            `headers`.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'PUT', path, **kwargs)


def simulate_options(app, path, **kwargs):
    """Simulates an OPTIONS request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'OPTIONS', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'OPTIONS', path, **kwargs)


def simulate_patch(app, path, **kwargs):
    """Simulates a PATCH request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'PATCH', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        body (str): A string to send as the body of the request.
            Accepts both byte strings and Unicode strings
            (default: ``None``). If a Unicode string is provided,
            it will be encoded as UTF-8 in the request.
        json(JSON serializable): A JSON document to serialize as the
            body of the request (default: ``None``). If specified,
            overrides `body` and the Content-Type header in
            `headers`.
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'PATCH', path, **kwargs)


def simulate_delete(app, path, **kwargs):
    """Simulates a DELETE request to a WSGI application.

    Equivalent to::

         simulate_request(app, 'DELETE', path, **kwargs)

    Args:
        app (callable): The WSGI application to call
        path (str): The URL path to request

    Keyword Args:
        params (dict): A dictionary of query string parameters,
            where each key is a parameter name, and each value is
            either a ``str`` or something that can be converted
            into a ``str``, or a list of such values. If a ``list``,
            the value will be converted to a comma-delimited string
            of values (e.g., 'thing=1,2,3').
        params_csv (bool): Set to ``False`` to encode list values
            in query string params by specifying multiple instances
            of the parameter (e.g., 'thing=1&thing=2&thing=3').
            Otherwise, parameters will be encoded as comma-separated
            values (e.g., 'thing=1,2,3'). Defaults to ``True``.
        headers (dict): Additional headers to include in the request
            (default: ``None``)
        protocol: The protocol to use for the URL scheme
            (default: 'http')
        host(str): A string to use for the hostname part of the fully qualified
            request URL (default: 'falconframework.org')
        remote_addr (str): A string to use as the remote IP address for the
            request (default: '127.0.0.1')
        extras (dict): Additional CGI variables to add to the WSGI ``environ``
            dictionary for the request (default: ``None``)
    """
    return simulate_request(app, 'DELETE', path, **kwargs)


class TestClient(object):
    """Simulates requests to a WSGI application.

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
        app (callable): A WSGI application to target when simulating
            requests


    Keyword Arguments:
        headers (dict): Default headers to set on every request (default
            ``None``). These defaults may be overridden by passing values
            for the same headers to one of the `simulate_*()` methods.
    """

    def __init__(self, app, headers=None):
        self.app = app
        self._default_headers = headers

    def simulate_get(self, path='/', **kwargs):
        """Simulates a GET request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_get`)
        """
        return self.simulate_request('GET', path, **kwargs)

    def simulate_head(self, path='/', **kwargs):
        """Simulates a HEAD request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_head`)
        """
        return self.simulate_request('HEAD', path, **kwargs)

    def simulate_post(self, path='/', **kwargs):
        """Simulates a POST request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_post`)
        """
        return self.simulate_request('POST', path, **kwargs)

    def simulate_put(self, path='/', **kwargs):
        """Simulates a PUT request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_put`)
        """
        return self.simulate_request('PUT', path, **kwargs)

    def simulate_options(self, path='/', **kwargs):
        """Simulates an OPTIONS request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_options`)
        """
        return self.simulate_request('OPTIONS', path, **kwargs)

    def simulate_patch(self, path='/', **kwargs):
        """Simulates a PATCH request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_patch`)
        """
        return self.simulate_request('PATCH', path, **kwargs)

    def simulate_delete(self, path='/', **kwargs):
        """Simulates a DELETE request to a WSGI application.

        (See also: :py:meth:`falcon.testing.simulate_delete`)
        """
        return self.simulate_request('DELETE', path, **kwargs)

    def simulate_request(self, *args, **kwargs):
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

        if compat.PY2 and 'headers' in kwargs:
            for key, value in kwargs['headers'].items():
                kwargs['headers'][key] = str(value) if isinstance(value, unicode) else value

        return simulate_request(self.app, *args, **kwargs)
