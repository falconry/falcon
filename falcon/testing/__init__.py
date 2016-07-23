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

"""Testing utilities.

This package contains various test classes and utility functions to
support functional testing for both Falcon-based apps and the Falcon
framework itself::

    from falcon import testing
    from myapp import app

    class TestMyApp(testing.TestCase):
        def setUp(self):
            super(TestMyApp, self).setUp()
            self.api = app.create_api()

    def test_get_message(self):
        doc = {u'message': u'Hello world!'}

        result = self.simulate_get('/messages/42')
        self.assertEqual(result.json, doc)

For additional examples, see also Falcon's own test suite.
"""

# Hoist classes and functions into the falcon.testing namespace
from falcon.testing.base import TestBase  # NOQA
from falcon.testing.helpers import *  # NOQA
from falcon.testing.resource import capture_responder_args  # NOQA
from falcon.testing.resource import SimpleTestResource, TestResource  # NOQA
from falcon.testing.srmock import StartResponseMock  # NOQA
from falcon.testing.test_case import Result, TestCase  # NOQA
