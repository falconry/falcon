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

import os
import unittest
import warnings

import falcon
import falcon.request
from falcon.testing.client import Result  # NOQA
from falcon.testing.client import TestClient

base_case = os.environ.get('FALCON_BASE_TEST_CASE')

if base_case and 'testtools.TestCase' in base_case:
    try:
        import testtools

        BaseTestCase = testtools.TestCase
    except ImportError:
        BaseTestCase = unittest.TestCase
elif base_case is None:
    try:
        import testtools

        warnings.warn(
            'Support for testtools is deprecated and will be removed in Falcon 5.0.',
            DeprecationWarning,
        )
        BaseTestCase = testtools.TestCase
    except ImportError:
        BaseTestCase = unittest.TestCase
else:
    BaseTestCase = unittest.TestCase


class TestCase(unittest.TestCase, TestClient):
    """Extends ``unittest`` to support WSGI/ASGI functional testing.

    Note:
        This class uses ``unittest`` by default, but you may use ``pytest``
        to run ``unittest.TestCase`` instances, allowing a hybrid approach.

    Recommended:
        We recommend using **pytest** alongside **unittest** for testing.
        See our tutorial on using pytest.

    This base class provides extra functionality for unittest-style test cases,
    helping simulate WSGI or ASGI requests without spinning up a web server. Various
    simulation methods are derived from :class:`falcon.testing.TestClient`.

    Simply inherit from this class in your test case classes instead of
    ``unittest.TestCase``.

    For example::

        from falcon import testing
        import myapp

        class MyTestCase(testing.TestCase):
            def setUp(self):
                super(MyTestCase, self).setUp()

                # Assume the hypothetical `myapp` package has a
                # function called `create()` to initialize and
                # return a `falcon.App` instance.
                self.app = myapp.create()

        class TestMyApp(MyTestCase):
            def test_get_message(self):
                doc = {'message': 'Hello world!'}

                result = self.simulate_get('/messages/42')
                self.assertEqual(result.json, doc)
    """

    __test__ = True

    app: falcon.App
    """A WSGI or ASGI application to target when simulating
    requests (defaults to ``falcon.App()``). When testing your
    application, you will need to set this to your own instance
    of :class:`falcon.App` or :class:`falcon.asgi.App`. For
    example::

        from falcon import testing
        import myapp

        class MyTestCase(testing.TestCase):
            def setUp(self):
                super(MyTestCase, self).setUp()

                # Assume the hypothetical `myapp` package has a
                # function called `create()` to initialize and
                # return a `falcon.App` instance.
                self.app = myapp.create()
    """

    def setUp(self) -> None:
        super(TestCase, self).setUp()

        app = falcon.App()

        # NOTE(kgriffs): Don't use super() to avoid triggering
        # unittest.TestCase.__init__()
        TestClient.__init__(self, app)
