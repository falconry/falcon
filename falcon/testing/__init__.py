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

"""Functional testing framework for Falcon apps and Falcon itself.

Falcon's testing module contains various test classes and utility
functions to support functional testing for both Falcon-based apps and
the Falcon framework itself.

The testing framework supports both unittest and pytest::

    # -----------------------------------------------------------------
    # unittest
    # -----------------------------------------------------------------

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


    # -----------------------------------------------------------------
    # pytest
    # -----------------------------------------------------------------

    from falcon import testing
    import pytest

    import myapp


    # Depending on your testing strategy and how your application
    # manages state, you may be able to broaden the fixture scope
    # beyond the default 'function' scope used in this example.

    @pytest.fixture()
    def client():
        # Assume the hypothetical `myapp` package has a function called
        # `create()` to initialize and return a `falcon.API` instance.
        return testing.TestClient(myapp.create())


    def test_get_message(client):
        doc = {u'message': u'Hello world!'}

        result = client.simulate_get('/messages/42')
        assert result.json == doc
"""

# Hoist classes and functions into the falcon.testing namespace
from falcon.testing.client import *  # NOQA
from falcon.testing.helpers import *  # NOQA
from falcon.testing.resource import capture_responder_args, set_resp_defaults  # NOQA
from falcon.testing.resource import SimpleTestResource  # NOQA
from falcon.testing.srmock import StartResponseMock  # NOQA
from falcon.testing.test_case import TestCase  # NOQA
