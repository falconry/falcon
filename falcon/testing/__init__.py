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
            # return a `falcon.App` instance.
            self.app = myapp.create()


    class TestMyApp(MyTestCase):
        def test_get_message(self):
            doc = {'message': 'Hello world!'}

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
        # `create()` to initialize and return a `falcon.App` instance.
        return testing.TestClient(myapp.create())


    def test_get_message(client):
        doc = {'message': 'Hello world!'}

        result = client.simulate_get('/messages/42')
        assert result.json == doc
"""

# Hoist classes and functions into the falcon.testing namespace
from falcon import util as _util
from falcon.testing.client import ASGIConductor
from falcon.testing.client import Cookie
from falcon.testing.client import Result
from falcon.testing.client import ResultBodyStream
from falcon.testing.client import simulate_delete
from falcon.testing.client import simulate_get
from falcon.testing.client import simulate_head
from falcon.testing.client import simulate_options
from falcon.testing.client import simulate_patch
from falcon.testing.client import simulate_post
from falcon.testing.client import simulate_put
from falcon.testing.client import simulate_request
from falcon.testing.client import StreamedResult
from falcon.testing.client import TestClient
from falcon.testing.helpers import ASGILifespanEventEmitter
from falcon.testing.helpers import ASGIRequestEventEmitter
from falcon.testing.helpers import ASGIResponseEventCollector
from falcon.testing.helpers import ASGIWebSocketSimulator
from falcon.testing.helpers import closed_wsgi_iterable
from falcon.testing.helpers import create_asgi_req
from falcon.testing.helpers import create_environ
from falcon.testing.helpers import create_req
from falcon.testing.helpers import create_scope
from falcon.testing.helpers import create_scope_ws
from falcon.testing.helpers import DEFAULT_HOST
from falcon.testing.helpers import DEFAULT_UA
from falcon.testing.helpers import get_encoding_from_headers
from falcon.testing.helpers import get_unused_port
from falcon.testing.helpers import rand_string
from falcon.testing.helpers import redirected
from falcon.testing.resource import capture_responder_args
from falcon.testing.resource import capture_responder_args_async
from falcon.testing.resource import set_resp_defaults
from falcon.testing.resource import set_resp_defaults_async
from falcon.testing.resource import SimpleTestResource
from falcon.testing.resource import SimpleTestResourceAsync
from falcon.testing.srmock import StartResponseMock
from falcon.testing.test_case import TestCase

# NOTE(kgriffs): Alias for backwards-compatibility with Falcon 0.2
# TODO: remove in falcon 4
httpnow = _util.http_now
