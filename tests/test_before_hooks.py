import json
import io

import falcon
import falcon.testing as testing


def validate(req, resp, params):
    raise falcon.HTTPBadRequest('Invalid thing', 'Your thing was not '
                                'formatted correctly.')


def validate_param(req, resp, params):
    limit = req.get_param_as_int('limit')
    if limit and int(limit) > 100:
        raise falcon.HTTPBadRequest('Out of range', 'limit must be <= 100')


def validate_field(req, resp, params):
    try:
        params['id'] = int(params['id'])
    except ValueError:
        raise falcon.HTTPBadRequest('Invalid ID', 'ID was not valid.')


def parse_body(req, resp, params):
    length = req.content_length or 0
    if length != 0:
        params['doc'] = json.load(io.TextIOWrapper(req.stream, 'utf-8'))


def bunnies(req, resp, params):
    params['bunnies'] = 'fuzzy'


def frogs(req, resp, params):
    if 'bunnies' in params:
        params['bunnies'] = 'fluffy'

    params['frogs'] = 'not fluffy'


class WrappedRespondersResource(object):

    @falcon.before(validate_param)
    @falcon.before(parse_body)
    def on_get(self, req, resp, doc):
        self.req = req
        self.resp = resp
        self.doc = doc

    @falcon.before(validate)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp


@falcon.before(bunnies)
class WrappedClassResource(object):

    # Test non-callable should be skipped by decorator
    on_patch = {}

    @falcon.before(validate_param)
    def on_get(self, req, resp, bunnies):
        self.req = req
        self.resp = resp
        self.bunnies = bunnies

    @falcon.before(validate_param)
    def on_head(self, req, resp, bunnies):
        self.req = req
        self.resp = resp
        self.bunnies = bunnies


class TestFieldResource(object):

    @falcon.before(validate_field)
    def on_get(self, req, resp, id):
        self.id = id


class BunnyResource(object):

    def on_get(self, req, resp, bunnies):
        self.bunnies = bunnies


class ZooResource(object):

    def on_get(self, req, resp, bunnies, frogs):
        self.bunnies = bunnies
        self.frogs = frogs


class TestHooks(testing.TestBase):

    def before(self):
        self.resource = WrappedRespondersResource()
        self.api.add_route(self.test_route, self.resource)

        self.field_resource = TestFieldResource()
        self.api.add_route('/queue/{id}/messages', self.field_resource)

        self.wrapped_resource = WrappedClassResource()
        self.api.add_route('/wrapped', self.wrapped_resource)

    def test_global_hook(self):
        self.assertRaises(TypeError, falcon.API, None, 0)
        self.assertRaises(TypeError, falcon.API, None, {})

        self.api = falcon.API(before=bunnies)
        zoo_resource = BunnyResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual('fuzzy', zoo_resource.bunnies)

    def test_multiple_global_hook(self):
        self.api = falcon.API(before=[bunnies, frogs])
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual('fluffy', zoo_resource.bunnies)
        self.assertEqual('not fluffy', zoo_resource.frogs)

    def test_input_validator(self):
        self.simulate_request(self.test_route, method='PUT')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_param_validator(self):
        self.simulate_request(self.test_route, query_string='?limit=10',
                              body='{}')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_request(self.test_route, query_string='?limit=101')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_field_validator(self):
        self.simulate_request('/queue/10/messages')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(self.field_resource.id, 10)

        self.simulate_request('/queue/bogus/messages')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_parser(self):
        self.simulate_request(self.test_route,
                              body=json.dumps({'animal': 'falcon'}))

        self.assertEqual(self.resource.doc, {'animal': 'falcon'})

    def test_wrapped_resource(self):
        self.simulate_request('/wrapped', method='PATCH')
        self.assertEqual(falcon.HTTP_405, self.srmock.status)

        self.simulate_request('/wrapped', query_string='?limit=10')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual('fuzzy', self.wrapped_resource.bunnies)

        self.simulate_request('/wrapped', method='HEAD')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual('fuzzy', self.wrapped_resource.bunnies)

        self.simulate_request('/wrapped', query_string='?limit=101')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        self.assertEqual('fuzzy', self.wrapped_resource.bunnies)
