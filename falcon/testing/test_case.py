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
from falcon.testing.client import TestClient
from falcon.testing.client import Result  # NOQA - hoist for backwards compat


class TestCase(unittest.TestCase, TestClient):
    """Extends :py:mod:`unittest` to support WSGI functional testing.

    Note:
        If available, uses :py:mod:`testtools` in lieu of
        :py:mod:`unittest`.

    This base class provides some extra plumbing for unittest-style
    test cases, to help simulate WSGI calls without having to spin up
    an actual web server. Various simulation methods are derived
    from :py:class:`falcon.testing.TestClient`.

    Simply inherit from this class in your test case classes instead of
    :py:class:`unittest.TestCase` or :py:class:`testtools.TestCase`.

    Attributes:
        app (object): A WSGI application to target when simulating
            requests (default: ``falcon.API()``). When testing your
            application, you will need to set this to your own instance
            of ``falcon.API``. For example::

                from falcon import testing
                import myapp


                class MyTestCase(testing.TestCase):
                    def setUp(self):
                        super(MyTestCase, self).setUp()

                        # Assume the hypothetical `myapp` package has a
                        # function called `create()` to initialize and
                        # return a `falcon.API` instance.
                        self.app = myapp.create()


                class TestMyApp(MyTestCase):
                    def test_get_message(self):
                        doc = {u'message': u'Hello world!'}

                        result = self.simulate_get('/messages/42')
                        self.assertEqual(result.json, doc)
    """

    def setUp(self):
        super(TestCase, self).setUp()

        app = falcon.API()

        # NOTE(kgriffs): Don't use super() to avoid triggering
        # unittest.TestCase.__init__()
        TestClient.__init__(self, app)

        # Reset to simulate "restarting" the WSGI container
        falcon.request._maybe_wrap_wsgi_stream = True

    # NOTE(warsaw): Pythons earlier than 2.7 do not have a
    # self.assertIn() method, so use this compatibility function
    # instead.
    if not hasattr(unittest.TestCase, 'assertIn'):  # pragma: nocover
        def assertIn(self, a, b):
            self.assertTrue(a in b)
