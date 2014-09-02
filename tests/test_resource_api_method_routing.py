# Copyright 2013 IBM Corp
#
# Author: Tong Li <litong01@us.ibm.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import falcon
from falcon import resource_api
import falcon.testing as testing

HTTP_METHODS = (
    'CONNECT',
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'POST',
    'PUT',
    'TRACE',
    'PATCH'
)


class ThingsResource(object):
    def __init__(self):
        self.called = False

        # Test non-callable attribute
        self.on_patch = {}

    @resource_api.Restify(path='/v2.0/tests/{id}/{sid}', method='get')
    def onget(self, req, resp, sid, id):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204

    @resource_api.Restify(path='/v2.0/tests/{id}/{sid}', method='head')
    def onhead(self, req, resp, id, sid):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_204

    @resource_api.Restify(path='/v2.0/tests/{id}/{sid}', method='put')
    def onput(self, req, resp, id, sid):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_201

    def nonput(self, req, resp, id, sid):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_201

    def on_post(self, req, resp, sid, id):
        self.called = True

        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_201


class TestResourceAPIHttpMethodRouting(testing.TestBase):

    def before(self):
        self.api = resource_api.ResourceAPI()
        self.resource_things = ThingsResource()
        self.api.add_route(self.resource_things)

    def test_bad_path_resource(self):
        try:
            class SomeClass(object):
                @resource_api.Restify(path='', method='post')
                def onput_invalid_path(req, resp, id, sid):
                    pass
            # if we reach this point, we have not caused an exception,
            # fail the test case.
            self.assertEqual(True, False)
        except Exception:
            # except this to fail.
            pass

    def test_bad_method_resource(self):
        try:
            class SomeClass(object):
                @resource_api.Restify(path='/some', method='not-nice')
                def onput_invalid_method(req, resp, id, sid):
                    pass
            self.assertEqual(True, False)
        except Exception:
            # expect this to fail with exception
            pass

    def test_get(self):
        self.simulate_request('/v2.0/tests/s100/10', method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertTrue(self.resource_things.called)

    def test_put(self):
        self.simulate_request('/v2.0/tests/100/6', method='PUT')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertTrue(self.resource_things.called)

    def test_post_not_allowed(self):
        self.simulate_request('/v2.0/tests', method='POST')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)
        self.assertFalse(self.resource_things.called)

    def test_bogus_method(self):
        self.simulate_request('/v2.0/tests', method=self.getUniqueString())
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_add_invalid_resource(self):
        try:
            self.api.add_route(None)
            self.assertEqual(True, False)
        except Exception:
            # expect this to fail with exception
            pass
