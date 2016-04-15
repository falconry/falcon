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

import json
import wsgiref.validate

try:
    import testtools as unittest
except ImportError:  # pragma: nocover
    import unittest

import falcon
import falcon.request
from falcon.util import CaseInsensitiveDict
from falcon.testing.srmock import StartResponseMock
from falcon.testing.helpers import create_environ, get_encoding_from_headers


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
            containing all the headers in the response
        encoding (str): Text encoding of the response body, or ``None``
            if the encoding can not be determined.
        content (bytes): Raw response body, or ``bytes`` if the
            response body was empty.
        text (str): Decoded response body of type ``unicode``
            under Python 2.6 and 2.7, and of type ``str`` otherwise.
            Raises an error if the response encoding can not be
            determined.
        json (dict): Deserialized JSON body. Raises an error if the
            response is not JSON.
    """

    def __init__(self, iterable, status, headers):
        self._text = None

        self._content = b''.join(iterable)
        if hasattr(iterable, 'close'):
            iterable.close()

        self._status = status
        self._status_code = int(status[:3])
        self._headers = CaseInsensitiveDict(headers)

        self._encoding = get_encoding_from_headers(self._headers)

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
                    msg = 'Response did not specify a content encoding'
                    raise RuntimeError(msg)

                self._text = self.content.decode(self.encoding)

        return self._text

    @property
    def json(self):
        return json.loads(self.text)


class TestCase(unittest.TestCase):
    """Extends :py:mod:`unittest` to support WSGI functional testing.

    Note:
        If available, uses :py:mod:`testtools` in lieu of
        :py:mod:`unittest`.

    This base class provides some extra plumbing for unittest-style
    test cases, to help simulate WSGI calls without having to spin up
    an actual web server. Simply inherit from this class in your test
    case classes instead of :py:class:`unittest.TestCase` or
    :py:class:`testtools.TestCase`.

    Attributes:
        api_class (class): An API class to use when instantiating
            the ``api`` instance (default: :py:class:`falcon.API`)
        api (object): An API instance to target when simulating
            requests (default: ``self.api_class()``)
    """

    api_class = None

    def setUp(self):
        super(TestCase, self).setUp()

        if self.api_class is None:
            self.api = falcon.API()
        else:
            self.api = self.api_class()

        # Reset to simulate "restarting" the WSGI container
        falcon.request._maybe_wrap_wsgi_stream = True

    # NOTE(warsaw): Pythons earlier than 2.7 do not have a
    # self.assertIn() method, so use this compatibility function
    # instead.
    if not hasattr(unittest.TestCase, 'assertIn'):  # pragma: nocover
        def assertIn(self, a, b):
            self.assertTrue(a in b)

    def simulate_get(self, path='/', **kwargs):
        """Simulates a GET request to a WSGI application.

        Equivalent to ``simulate_request('GET', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
        """
        return self.simulate_request('GET', path, **kwargs)

    def simulate_head(self, path='/', **kwargs):
        """Simulates a HEAD request to a WSGI application.

        Equivalent to ``simulate_request('HEAD', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
        """
        return self.simulate_request('HEAD', path, **kwargs)

    def simulate_post(self, path='/', **kwargs):
        """Simulates a POST request to a WSGI application.

        Equivalent to ``simulate_request('POST', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
            body (str): A string to send as the body of the request.
                Accepts both byte strings and Unicode strings
                (default: ``None``). If a Unicode string is provided,
                it will be encoded as UTF-8 in the request.
        """
        return self.simulate_request('POST', path, **kwargs)

    def simulate_put(self, path='/', **kwargs):
        """Simulates a PUT request to a WSGI application.

        Equivalent to ``simulate_request('PUT', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
            body (str): A string to send as the body of the request.
                Accepts both byte strings and Unicode strings
                (default: ``None``). If a Unicode string is provided,
                it will be encoded as UTF-8 in the request.
        """
        return self.simulate_request('PUT', path, **kwargs)

    def simulate_options(self, path='/', **kwargs):
        """Simulates an OPTIONS request to a WSGI application.

        Equivalent to ``simulate_request('OPTIONS', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
        """
        return self.simulate_request('OPTIONS', path, **kwargs)

    def simulate_patch(self, path='/', **kwargs):
        """Simulates a PATCH request to a WSGI application.

        Equivalent to ``simulate_request('PATCH', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
            body (str): A string to send as the body of the request.
                Accepts both byte strings and Unicode strings
                (default: ``None``). If a Unicode string is provided,
                it will be encoded as UTF-8 in the request.
        """
        return self.simulate_request('PATCH', path, **kwargs)

    def simulate_delete(self, path='/', **kwargs):
        """Simulates a DELETE request to a WSGI application.

        Equivalent to ``simulate_request('DELETE', ...)``

        Args:
            path (str): The URL path to request (default: '/')

        Keyword Args:
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
        """
        return self.simulate_request('DELETE', path, **kwargs)

    def simulate_request(self, method='GET', path='/', query_string=None,
                         headers=None, body=None, file_wrapper=None):
        """Simulates a request to a WSGI application.

        Performs a WSGI request directly against ``self.api``.

        Keyword Args:
            method (str): The HTTP method to use in the request
                (default: 'GET')
            path (str): The URL path to request (default: '/')
            query_string (str): A raw query string to include in the
                request (default: ``None``)
            headers (dict): Additional headers to include in the request
                (default: ``None``)
            body (str): A string to send as the body of the request.
                Accepts both byte strings and Unicode strings
                (default: ``None``). If a Unicode string is provided,
                it will be encoded as UTF-8 in the request.
            file_wrapper (callable): Callable that returns an iterable,
                to be used as the value for *wsgi.file_wrapper* in the
                environ (default: ``None``).

        Returns:
            :py:class:`~.Result`: The result of the request
        """

        if not path.startswith('/'):
            raise ValueError("path must start with '/'")

        if query_string and query_string.startswith('?'):
            raise ValueError("query_string should not start with '?'")

        if '?' in path:
            # NOTE(kgriffs): We could allow this, but then we'd need
            #   to define semantics regarding whether the path takes
            #   precedence over the query_string. Also, it would make
            #   tests less consistent, since there would be "more than
            #   one...way to do it."
            raise ValueError(
                'path may not contain a query string. Please use the '
                'query_string parameter instead.'
            )

        env = create_environ(
            method=method,
            path=path,
            query_string=(query_string or ''),
            headers=headers,
            body=body,
            file_wrapper=file_wrapper,
        )

        srmock = StartResponseMock()
        validator = wsgiref.validate.validator(self.api)
        iterable = validator(env, srmock)

        result = Result(iterable, srmock.status, srmock.headers)

        return result
