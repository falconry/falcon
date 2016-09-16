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

"""Test case base class (deprecated)."""

import itertools

try:
    import testtools as unittest
except ImportError:  # pragma: nocover
    import unittest

import falcon
import falcon.request
from falcon.testing.helpers import create_environ
from falcon.testing.srmock import StartResponseMock


# NOTE(kgriffs): Since this class is deprecated and we will be using it
# less and less for Falcon's own tests, coverage may be reduced, hence
# the pragma to ignore coverage errors from now on.
class TestBase(unittest.TestCase):  # pragma nocover
    """Extends :py:mod:`unittest` to support WSGI functional testing.

    Warning:
        This class has been deprecated and will be removed in a future
        release. Please use :py:class:`~.TestCase`
        instead.

    Note:
        If available, uses :py:mod:`testtools` in lieu of
        :py:mod:`unittest`.

    This base class provides some extra plumbing for unittest-style
    test cases, to help simulate WSGI calls without having to spin up
    an actual web server. Simply inherit from this class in your test
    case classes instead of :py:class:`unittest.TestCase` or
    :py:class:`testtools.TestCase`.

    Attributes:
        api (falcon.API): An API instance to target when simulating
            requests. Defaults to ``falcon.API()``.
        srmock (falcon.testing.StartResponseMock): Provides a callable
            that simulates the behavior of the `start_response` argument
            that the server would normally pass into the WSGI app. The
            mock object captures various information from the app's
            response to the simulated request.
        test_route (str): A simple, generated path that a test
            can use to add a route to the API.
    """

    api_class = falcon.API
    srmock_class = StartResponseMock

    def setUp(self):
        """Initializer, unittest-style"""
        super(TestBase, self).setUp()
        self._id = itertools.count(0)
        self.api = self.api_class()
        self.srmock = self.srmock_class()
        self.test_route = '/{0}'.format(next(self._id))

        # Reset to simulate "restarting" the WSGI container
        falcon.request._maybe_wrap_wsgi_stream = True

        before = getattr(self, 'before', None)
        if callable(before):
            before()

    def tearDown(self):
        """Destructor, unittest-style"""

        after = getattr(self, 'after', None)
        if callable(after):
            after()

        super(TestBase, self).tearDown()

    # NOTE(warsaw): Pythons earlier than 2.7 do not have a self.assertIn()
    # method, so use this compatibility function instead.
    if not hasattr(unittest.TestCase, 'assertIn'):  # pragma: nocover
        def assertIn(self, a, b):
            self.assertTrue(a in b)

    def simulate_request(self, path, decode=None, **kwargs):
        """Simulates a request to `self.api`.

        Args:
            path (str): The path to request.
            decode (str, optional): If this is set to a character encoding,
                such as 'utf-8', `simulate_request` will assume the
                response is a single byte string, and will decode it as the
                result of the request, rather than simply returning the
                standard WSGI iterable.
            kwargs (optional): Same as those defined for
                `falcon.testing.create_environ`.

        """

        if not path:
            path = '/'

        result = self.api(create_environ(path=path, **kwargs),
                          self.srmock)

        if decode is not None:
            if not result:
                return ''

            return result[0].decode(decode)

        return result
