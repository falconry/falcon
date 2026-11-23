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

from typing import Any

try:
    # For backward compatibility: testtools may still be used if installed,
    # though pytest is now the recommended testing framework for Falcon apps.
    import testtools as unittest
except ImportError:  # pragma: nocover
    import unittest

import falcon
import falcon.request

# TODO: Hoist for backwards compat. Remove in Falcon 5.0.
from falcon.testing.client import Result  # NOQA
from falcon.testing.client import TestClient


class TestCase(unittest.TestCase, TestClient):  # type: ignore[misc]
    """Extends :mod:`unittest` to support WSGI/ASGI functional testing.

    For modern projects, we recommend using :mod:`pytest` with
    :class:`falcon.testing.TestClient` directly, as shown in the
    `tutorial <testing_tutorial>`_.

    For projects using unittest-style test classes, this base class provides
    extra plumbing to help simulate WSGI or ASGI requests without having to
    spin up an actual web server. Various simulation methods are derived from
    :class:`falcon.testing.TestClient`.

    Note:
        This class supports :class:`unittest.TestCase`, and for backward
        compatibility, :class:`testtools.TestCase` (if available).

    Simply inherit from this class in your test case classes instead of
    :class:`unittest.TestCase`::

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

    # NOTE(vytas): Parametrize with [Any, Any] because the app under test may
    #   use custom Request/Response subclasses.
    # TODO(vytas): A future change could make TestCase generic over the app's
    #   request/response types (leveraging TypeVar defaults on Python 3.13+).
    app: falcon.App[Any, Any]
    """A WSGI or ASGI application to target when simulating requests
    (defaults to ``falcon.App()``).

    When testing your application, you will need to set this to your own
    instance of :class:`falcon.App` or :class:`falcon.asgi.App`. See the
    class docstring for an example.
    """

    def setUp(self) -> None:
        super().setUp()

        app = falcon.App()

        # NOTE(kgriffs): Don't use super() to avoid triggering
        # unittest.TestCase.__init__()
        TestClient.__init__(self, app)
