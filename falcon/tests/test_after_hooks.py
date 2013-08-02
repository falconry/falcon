import json

import falcon
import falcon.testing as testing


def validate_output(req, resp):
    raise falcon.HTTPError(falcon.HTTP_723, title=None)


def serialize_body(req, resp):
    body = resp.body
    if body is not None:
        resp.body = json.dumps(body)
    else:
        resp.body = 'Nothing to see here. Move along.'


def fluffiness(req, resp):
    resp.body = 'fluffy'


def cuteness(req, resp):
    if resp.body == 'fluffy':
        resp.body += ' and cute'


class WrappedRespondersResource(object):

    @falcon.after(serialize_body)
    @falcon.after(validate_output)
    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    @falcon.after(serialize_body)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp
        resp.body = {'animal': 'falcon'}


@falcon.after(cuteness)
@falcon.after(fluffiness)
class WrappedClassResource(object):

    # Test that the decorator skips non-callables
    on_post = False

    def __init__(self):
        # Test that the decorator skips non-callables
        self.on_patch = []

    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    def on_head(self, req, resp):
        self.req = req
        self.resp = resp


class ZooResource(object):

    def on_get(self, req, resp):
        self.resp = resp


class TestHooks(testing.TestBase):

    def before(self):
        self.resource = WrappedRespondersResource()
        self.api.add_route(self.test_route, self.resource)

        self.wrapped_resource = WrappedClassResource()
        self.api.add_route('/wrapped', self.wrapped_resource)

    def test_global_hook(self):
        self.assertRaises(TypeError, falcon.API, None, {})
        self.assertRaises(TypeError, falcon.API, None, 0)

        self.api = falcon.API(after=fluffiness)
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual(b'fluffy', zoo_resource.resp.body_encoded)

    def test_multiple_global_hook(self):
        self.api = falcon.API(after=[fluffiness, cuteness])
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual(b'fluffy and cute', zoo_resource.resp.body_encoded)

    def test_output_validator(self):
        self.simulate_request(self.test_route)
        self.assertEqual(falcon.HTTP_723, self.srmock.status)
        self.assertEqual(None, self.resource.resp.body_encoded)

    def test_serializer(self):
        self.simulate_request(self.test_route, method='PUT')

        actual_body = self.resource.resp.body_encoded
        self.assertEqual(b'{"animal": "falcon"}', actual_body)

    def test_wrapped_resource(self):
        expected = b'fluffy and cute'

        self.simulate_request('/wrapped')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(expected, self.wrapped_resource.resp.body_encoded)

        self.simulate_request('/wrapped', method='HEAD')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_request('/wrapped', method='POST')
        self.assertEqual(falcon.HTTP_405, self.srmock.status)

        self.simulate_request('/wrapped', method='PATCH')
        self.assertEqual(falcon.HTTP_405, self.srmock.status)
