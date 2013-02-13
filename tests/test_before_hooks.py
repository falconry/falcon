import json
import io

import falcon
import falcon.testing as testing


def validate(req, resp):
    raise falcon.HTTPBadRequest('Invalid thing', 'Your thing was not '
                                'formatted correctly.')


def validate_param(req, resp):
    limit = req.get_param_as_int('limit')
    if limit and int(limit) > 100:
        raise falcon.HTTPBadRequest('Out of range', 'limit must be <= 100')


def validate_field(req, resp, id):
    try:
        id = int(id)
    except ValueError:
        raise falcon.HTTPBadRequest('Invalid ID', 'ID was not valid.')


def parse_body(req, resp):
    length = req.content_length or 0
    if length != 0:
        req.ext['doc'] = json.load(io.TextIOWrapper(req.stream, 'utf-8'))


def bunnies(req, resp):
    req.ext['bunnies'] = 'fuzzy'


def frogs(req, resp):
    req.ext['bunnies'] = 'fluffy'
    req.ext['frogs'] = 'not fluffy'


class WrappedRespondersResource(object):

    @falcon.before(validate_param)
    @falcon.before(parse_body)
    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    @falcon.before(validate)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp


@falcon.before(bunnies)
class WrappedClassResource(object):

    @falcon.before(validate_param)
    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    @falcon.before(validate_param)
    def on_head(self, req, resp):
        self.req = req
        self.resp = resp


class TestFieldResource(object):

    @falcon.before(validate_field)
    def on_get(self, req, resp, id):
        pass


class TestHooks(testing.TestSuite):

    def prepare(self):
        self.resource = WrappedRespondersResource()
        self.api.add_route(self.test_route, self.resource)
        self.api.add_route('/queue/{id}/messages', TestFieldResource())

        self.wrapped_resource = WrappedClassResource()
        self.api.add_route('/wrapped', self.wrapped_resource)

    def test_global_hook(self):
        self.resource = testing.TestResource()
        self.api = falcon.API(before=bunnies)
        self.api.add_route(self.test_route, self.resource)

        self.simulate_request(self.test_route)
        self.assertTrue(self.resource.called)
        self.assertEqual('fuzzy', self.resource.req.ext['bunnies'])

    def _test_multiple_global_hook(self):
        self.resource = testing.TestResource()
        self.api = falcon.API(before=[bunnies, frogs])
        self.api.add_route(self.test_route, self.resource)

        self.simulate_request(self.test_route)
        self.assertTrue(self.resource.called)
        self.assertEqual('fluffy', self.resource.req.ext['bunnies'])
        self.assertEqual('not fluffy', self.resource.req.ext['frogs'])

    def test_input_validator(self):
        self.simulate_request(self.test_route, method='PUT')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_param_validator(self):
        self.simulate_request(self.test_route, query_string='?limit=10')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_request(self.test_route, query_string='?limit=101')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_field_validator(self):
        self.simulate_request('/queue/10/messages')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_request('/queue/bogus/messages')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_parser(self):
        self.simulate_request(self.test_route,
                              body=json.dumps({'animal': 'falcon'}))

        req = self.resource.req

        self.assertEqual(req.ext['doc'], {'animal': 'falcon'})

    def test_wrapped_resource(self):
        self.simulate_request('/wrapped', query_string='?limit=10')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual('fuzzy', self.wrapped_resource.req.ext['bunnies'])

        self.simulate_request('/wrapped', query_string='?limit=101')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        self.assertEqual('fuzzy', self.wrapped_resource.req.ext['bunnies'])
