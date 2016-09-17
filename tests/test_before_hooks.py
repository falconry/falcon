import functools
import io
import json

import falcon
import falcon.testing as testing


def validate(req, resp, params):
    raise falcon.HTTPBadRequest('Invalid thing', 'Your thing was not '
                                'formatted correctly.')


def validate_param(req, resp, params):
    limit = req.get_param_as_int('limit')
    if limit and int(limit) > 100:
        raise falcon.HTTPBadRequest('Out of range', 'limit must be <= 100')


def resource_aware_validate_param(req, resp, resource, params):
    assert resource
    validate_param(req, resp, params)


class ResourceAwareValidateParam(object):
    def __call__(self, req, resp, resource, params):
        assert resource
        validate_param(req, resp, params)


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


def resource_aware_bunnies(req, resp, resource, params):
    assert resource
    bunnies(req, resp, params)


def frogs(req, resp, params):
    if 'bunnies' in params:
        params['bunnies'] = 'fluffy'

    params['frogs'] = 'not fluffy'


class Fish(object):
    def __call__(self, req, resp, params):
        params['fish'] = 'slippery'

    def hook(self, req, resp, resource, params):
        params['fish'] = 'wet'


# NOTE(kgriffs): Use partial methods for these next two in order
# to make sure we handle that correctly.
def things_in_the_head(header, value, req, resp, resource, params):
    resp.set_header(header, value)


bunnies_in_the_head = functools.partial(things_in_the_head,
                                        'X-Bunnies', 'fluffy')

frogs_in_the_head = functools.partial(things_in_the_head,
                                      'X-Frogs', 'not fluffy')


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

    _some_fish = Fish()

    # Test non-callable should be skipped by decorator
    on_patch = {}

    @falcon.before(validate_param)
    def on_get(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(validate_param)
    def on_head(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(_some_fish)
    def on_post(self, req, resp, fish, bunnies):
        self._capture(req, resp, bunnies)
        self.fish = fish

    @falcon.before(_some_fish.hook)
    def on_put(self, req, resp, fish, bunnies):
        self._capture(req, resp, bunnies)
        self.fish = fish

    def _capture(self, req, resp, bunnies):
        self.req = req
        self.resp = resp
        self.bunnies = bunnies


# NOTE(swistakm): we both both type of hooks (class and method)
# at once for the sake of simplicity
@falcon.before(resource_aware_bunnies)
class ClassResourceWithAwareHooks(object):
    hook_as_class = ResourceAwareValidateParam()

    @falcon.before(resource_aware_validate_param)
    def on_get(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(resource_aware_validate_param)
    def on_head(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(hook_as_class)
    def on_put(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(hook_as_class.__call__)
    def on_post(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    def _capture(self, req, resp, bunnies):
        self.req = req
        self.resp = resp
        self.bunnies = bunnies


class TestFieldResource(object):

    @falcon.before(validate_field)
    def on_get(self, req, resp, id):
        self.id = id


@falcon.before(bunnies)
@falcon.before(frogs)
@falcon.before(Fish())
@falcon.before(bunnies_in_the_head)
@falcon.before(frogs_in_the_head)
class ZooResource(object):

    def on_get(self, req, resp, bunnies, frogs, fish):
        self.bunnies = bunnies
        self.frogs = frogs
        self.fish = fish


class TestHooks(testing.TestCase):

    def setUp(self):
        super(TestHooks, self).setUp()

        self.resource = WrappedRespondersResource()
        self.api.add_route('/', self.resource)

        self.field_resource = TestFieldResource()
        self.api.add_route('/queue/{id}/messages', self.field_resource)

        self.wrapped_resource = WrappedClassResource()
        self.api.add_route('/wrapped', self.wrapped_resource)

        self.wrapped_aware_resource = ClassResourceWithAwareHooks()
        self.api.add_route('/wrapped_aware', self.wrapped_aware_resource)

    def test_multiple_resource_hooks(self):
        zoo_resource = ZooResource()
        self.api.add_route('/', zoo_resource)

        result = self.simulate_get('/')

        self.assertEqual('not fluffy', result.headers['X-Frogs'])
        self.assertEqual('fluffy', result.headers['X-Bunnies'])

        self.assertEqual('fluffy', zoo_resource.bunnies)
        self.assertEqual('not fluffy', zoo_resource.frogs)
        self.assertEqual('slippery', zoo_resource.fish)

    def test_input_validator(self):
        result = self.simulate_put('/')
        self.assertEqual(result.status_code, 400)

    def test_param_validator(self):
        result = self.simulate_get('/', query_string='limit=10', body='{}')
        self.assertEqual(result.status_code, 200)

        result = self.simulate_get('/', query_string='limit=101')
        self.assertEqual(result.status_code, 400)

    def test_field_validator(self):
        result = self.simulate_get('/queue/10/messages')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.field_resource.id, 10)

        result = self.simulate_get('/queue/bogus/messages')
        self.assertEqual(result.status_code, 400)

    def test_parser(self):
        self.simulate_get('/', body=json.dumps({'animal': 'falcon'}))
        self.assertEqual(self.resource.doc, {'animal': 'falcon'})

    def test_wrapped_resource(self):
        result = self.simulate_patch('/wrapped')
        self.assertEqual(result.status_code, 405)

        result = self.simulate_get('/wrapped', query_string='limit=10')
        self.assertEqual(result.status_code, 200)
        self.assertEqual('fuzzy', self.wrapped_resource.bunnies)

        result = self.simulate_head('/wrapped')
        self.assertEqual(result.status_code, 200)
        self.assertEqual('fuzzy', self.wrapped_resource.bunnies)

        result = self.simulate_post('/wrapped')
        self.assertEqual(result.status_code, 200)
        self.assertEqual('slippery', self.wrapped_resource.fish)

        result = self.simulate_get('/wrapped', query_string='limit=101')
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.wrapped_resource.bunnies, 'fuzzy')

    def test_wrapped_resource_with_hooks_aware_of_resource(self):
        result = self.simulate_patch('/wrapped_aware')
        self.assertEqual(result.status_code, 405)

        result = self.simulate_get('/wrapped_aware', query_string='limit=10')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.wrapped_aware_resource.bunnies, 'fuzzy')

        for method in ('HEAD', 'PUT', 'POST'):
            result = self.simulate_request(method, '/wrapped_aware')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(self.wrapped_aware_resource.bunnies, 'fuzzy')

        result = self.simulate_get('/wrapped_aware', query_string='limit=101')
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.wrapped_aware_resource.bunnies, 'fuzzy')
