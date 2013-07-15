"""Defines the TestSuite class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""
import itertools

try:
    import testtools as unittest
except ImportError:  # pragma: nocover
    import unittest

import falcon
from falcon.testing.srmock import StartResponseMock
from falcon.testing.helpers import create_environ


class TestBase(unittest.TestCase):
    """Scaffolding around testtools.TestCase for testing a Falcon API endpoint.

    Note: If testtools is not available, falls back to using unittest.

    Inherit from this and write your test methods. If the child class defines
    a before(self) method, this method will be called before executing each
    test method. Likewise, child classes may define an after(self) method to
    execute actions after each test method returns.

    Attributes:
        api: falcon.API instance used in simulating requests.
        srmock: falcon.testing.StartResponseMock instance used in
            simulating requests.
        test_route: Randomly-generated route string (path) that tests can
            use when wiring up resources.


    """

    def setUp(self):
        """Initializer, unittest-style"""

        super(TestBase, self).setUp()
        self._id = itertools.count(0)
        self.api = falcon.API()
        self.srmock = StartResponseMock()
        self.test_route = '/{0}'.format(next(self._id))

        before = getattr(self, 'before', None)
        if hasattr(before, '__call__'):
            before()

    def tearDown(self):
        """Destructor, unittest-style"""

        after = getattr(self, 'after', None)
        if hasattr(after, '__call__'):
            after()

        super(TestBase, self).tearDown()

    def simulate_request(self, path, **kwargs):
        """ Simulates a request.

        Simulates a request to the API for testing purposes.

        Args:
            path: Request path for the desired resource
            kwargs: Same as falcon.testing.create_environ()

        """

        if not path:
            path = '/'

        return self.api(create_environ(path=path, **kwargs),
                        self.srmock)
