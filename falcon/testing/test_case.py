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

"""unittest-style base class and utilities for test cases.

This package includes a unittest-style base class and requests-like
utilities for simulating and validating HTTP requests.
"""

try:
    import testtools as unittest
except ImportError:  # pragma: nocover
    import unittest

import falcon
import falcon.request
from falcon.testing import client
from falcon.testing.client import Result  # NOQA - hoist for backwards compat


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
        api_class (class): An API class or factory method to use when
            instantiating the ``api`` instance (default:
            :py:class:`falcon.API`).
        api (object): An API instance to target when simulating requests
            (default: ``self.api_class()``). When testing your
            application, you will need to overwrite this with your own
            instance of ``falcon.API``, or use `api_class` to specify a
            factory method for your application.
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
        return client.simulate_get(self.api, path, **kwargs)

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
        return client.simulate_head(self.api, path, **kwargs)

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
        return client.simulate_post(self.api, path, **kwargs)

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
        return client.simulate_put(self.api, path, **kwargs)

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
        return client.simulate_options(self.api, path, **kwargs)

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
        return client.simulate_patch(self.api, path, **kwargs)

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
        return client.simulate_delete(self.api, path, **kwargs)

    def simulate_request(self, *args, **kwargs):
        """Simulates a request to a WSGI application.

        Wraps :py:meth:`falcon.testing.simulate_request` to perform a
        WSGI request directly against ``self.api``. Equivalent to::

            falcon.testing.simulate_request(self.api, *args, **kwargs)
        """

        return client.simulate_request(self.api, *args, **kwargs)
