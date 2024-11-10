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

if 'DISABLE_TESTTOOLS' not in os.environ:
    try:
        import testtools

        warnings.warn(
            'Support for testtools is deprecated and will be removed in Falcon 5.0. '
            'Please migrate to unittest or pytest.',
            DeprecationWarning,
        )
        BaseTestCase = testtools.TestCase
    except ImportError:  # pragma: nocover
        BaseTestCase = unittest.TestCase

import falcon
import falcon.request
from falcon.testing.client import Result  # NOQA
from falcon.testing.client import TestClient


class TestCase(unittest.TestCase, TestClient):
    """Extends :mod:`unittest` to support WSGI/ASGI functional testing.

    Note:
        This class uses :mod:`unittest` by default. If :mod:`testtools`
        is available and the environment variable
        ``DISABLE_TESTTOOLS`` is **not** set, it will use :mod:`testtools` instead.
        **Support for testtools is deprecated and will be removed in Falcon 5.0.**

    Recommended:
        We recommend using **pytest** for testing Falcon applications.
        See our tutorial on using pytest.

    This base class provides some extra plumbing for unittest-style
    test cases, to help simulate WSGI or ASGI requests without having
    to spin up an actual web server. Various simulation methods are
    derived from :class:`falcon.testing.TestClient`.

    Simply inherit from this class in your test case classes instead of
    :class:`unittest.TestCase`.

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

    # NOTE(vytas): Here we have to restore __test__ to allow collecting tests!
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
