import functools
import io
import json

import pytest

import falcon
import falcon.testing as testing


def validate(req, resp, resource, params):
    assert resource
    raise falcon.HTTPBadRequest('Invalid thing', 'Your thing was not '
                                'formatted correctly.')


def validate_param(req, resp, resource, params, param_name, maxval=100):
    assert resource

    limit = req.get_param_as_int(param_name)
    if limit and int(limit) > maxval:
        msg = '{0} must be <= {1}'.format(param_name, maxval)
        raise falcon.HTTPBadRequest('Out of Range', msg)


class ResourceAwareValidateParam(object):
    def __call__(self, req, resp, resource, params):
        assert resource
        validate_param(req, resp, resource, params, 'limit')


def validate_field(req, resp, resource, params, field_name='test'):
    assert resource

    try:
        params[field_name] = int(params[field_name])
    except ValueError:
        raise falcon.HTTPBadRequest()


def parse_body(req, resp, resource, params):
    assert resource

    length = req.content_length or 0
    if length != 0:
        params['doc'] = json.load(io.TextIOWrapper(req.bounded_stream, 'utf-8'))


def bunnies(req, resp, resource, params):
    assert resource
    params['bunnies'] = 'fuzzy'


def frogs(req, resp, resource, params):
    assert resource

    if 'bunnies' in params:
        params['bunnies'] = 'fluffy'

    params['frogs'] = 'not fluffy'


class Fish(object):
    def __call__(self, req, resp, resource, params):
        assert resource
        params['fish'] = 'slippery'

    def hook(self, req, resp, resource, params):
        assert resource
        params['fish'] = 'wet'


# NOTE(kgriffs): Use partial methods for these next two in order
# to make sure we handle that correctly.
def things_in_the_head(header, value, req, resp, resource, params):
    resp.set_header(header, value)


bunnies_in_the_head = functools.partial(
    things_in_the_head,
    'X-Bunnies',
    'fluffy'
)

frogs_in_the_head = functools.partial(
    things_in_the_head,
    'X-Frogs',
    'not fluffy'
)


class WrappedRespondersResource(object):

    @falcon.before(validate_param, 'limit', 100)
    @falcon.before(parse_body)
    def on_get(self, req, resp, doc):
        self.req = req
        self.resp = resp
        self.doc = doc

    @falcon.before(validate)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp


class WrappedRespondersResourceChild(WrappedRespondersResource):

    @falcon.before(validate_param, 'x', maxval=1000)
    def on_get(self, req, resp):
        pass

    def on_put(self, req, resp):
        # Test passing no extra args
        super(WrappedRespondersResourceChild, self).on_put(req, resp)


@falcon.before(bunnies)
class WrappedClassResource(object):

    _some_fish = Fish()

    # Test non-callable should be skipped by decorator
    on_patch = {}

    @falcon.before(validate_param, 'limit')
    def on_get(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(validate_param, 'limit')
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


# NOTE(swistakm): we use both type of hooks (class and method)
# at once for the sake of simplicity
@falcon.before(bunnies)
class ClassResourceWithAwareHooks(object):
    hook_as_class = ResourceAwareValidateParam()

    @falcon.before(validate_param, 'limit', 10)
    def on_get(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(validate_param, 'limit')
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

    @falcon.before(validate_field, field_name='id')
    def on_get(self, req, resp, id):
        self.id = id


class TestFieldResourceChild(TestFieldResource):

    def on_get(self, req, resp, id):
        # Test passing a single extra arg
        super(TestFieldResourceChild, self).on_get(req, resp, id)


class TestFieldResourceChildToo(TestFieldResource):

    def on_get(self, req, resp, id):
        # Test passing a single kwarg, but no extra args
        super(TestFieldResourceChildToo, self).on_get(req, resp, id=id)


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


class ZooResourceChild(ZooResource):

    def on_get(self, req, resp):
        super(ZooResourceChild, self).on_get(
            req,
            resp,

            # Test passing a mixture of args and kwargs
            'fluffy',
            'not fluffy',
            fish='slippery'
        )


@pytest.fixture
def wrapped_aware_resource():
    return ClassResourceWithAwareHooks()


@pytest.fixture
def wrapped_resource():
    return WrappedClassResource()


@pytest.fixture
def resource():
    return WrappedRespondersResource()


@pytest.fixture
def client(resource):
    app = falcon.API()
    app.add_route('/', resource)
    return testing.TestClient(app)


@pytest.mark.parametrize('resource', [ZooResource(), ZooResourceChild()])
def test_multiple_resource_hooks(client, resource):
    client.app.add_route('/', resource)

    result = client.simulate_get('/')

    assert 'not fluffy' == result.headers['X-Frogs']
    assert 'fluffy' == result.headers['X-Bunnies']

    assert 'fluffy' == resource.bunnies
    assert 'not fluffy' == resource.frogs
    assert 'slippery' == resource.fish


def test_input_validator(client):
    result = client.simulate_put('/')
    assert result.status_code == 400


def test_input_validator_inherited(client):
    client.app.add_route('/', WrappedRespondersResourceChild())
    result = client.simulate_put('/')
    assert result.status_code == 400

    result = client.simulate_get('/', query_string='x=1000')
    assert result.status_code == 200

    result = client.simulate_get('/', query_string='x=1001')
    assert result.status_code == 400


def test_param_validator(client):
    result = client.simulate_get('/', query_string='limit=10', body='{}')
    assert result.status_code == 200

    result = client.simulate_get('/', query_string='limit=101')
    assert result.status_code == 400


@pytest.mark.parametrize(
    'resource',
    [
        TestFieldResource(),
        TestFieldResourceChild(),
        TestFieldResourceChildToo(),
    ]
)
def test_field_validator(client, resource):
    client.app.add_route('/queue/{id}/messages', resource)
    result = client.simulate_get('/queue/10/messages')
    assert result.status_code == 200
    assert resource.id == 10

    result = client.simulate_get('/queue/bogus/messages')
    assert result.status_code == 400


def test_parser(client, resource):
    client.simulate_get('/', body=json.dumps({'animal': 'falcon'}))
    assert resource.doc == {'animal': 'falcon'}


def test_wrapped_resource(client, wrapped_resource):
    client.app.add_route('/wrapped', wrapped_resource)
    result = client.simulate_patch('/wrapped')
    assert result.status_code == 405

    result = client.simulate_get('/wrapped', query_string='limit=10')
    assert result.status_code == 200
    assert 'fuzzy' == wrapped_resource.bunnies

    result = client.simulate_head('/wrapped')
    assert result.status_code == 200
    assert 'fuzzy' == wrapped_resource.bunnies

    result = client.simulate_post('/wrapped')
    assert result.status_code == 200
    assert 'slippery' == wrapped_resource.fish

    result = client.simulate_get('/wrapped', query_string='limit=101')
    assert result.status_code == 400
    assert wrapped_resource.bunnies == 'fuzzy'


def test_wrapped_resource_with_hooks_aware_of_resource(client, wrapped_aware_resource):
    client.app.add_route('/wrapped_aware', wrapped_aware_resource)

    result = client.simulate_patch('/wrapped_aware')
    assert result.status_code == 405

    result = client.simulate_get('/wrapped_aware', query_string='limit=10')
    assert result.status_code == 200
    assert wrapped_aware_resource.bunnies == 'fuzzy'

    for method in ('HEAD', 'PUT', 'POST'):
        result = client.simulate_request(method, '/wrapped_aware')
        assert result.status_code == 200
        assert wrapped_aware_resource.bunnies == 'fuzzy'

    result = client.simulate_get('/wrapped_aware', query_string='limit=11')
    assert result.status_code == 400
    assert wrapped_aware_resource.bunnies == 'fuzzy'


_another_fish = Fish()


def header_hook(req, resp, resource, params):
    value = resp.get_header('X-Hook-Applied') or '0'
    resp.set_header('X-Hook-Applied', str(int(value) + 1))


@falcon.before(header_hook)
class PiggybackingCollection(object):

    def __init__(self):
        self._items = {}
        self._sequence = 0

    @falcon.before(_another_fish.hook)
    def on_delete(self, req, resp, fish, itemid):
        del self._items[itemid]
        resp.set_header('X-Fish-Trait', fish)
        resp.status = falcon.HTTP_NO_CONTENT

    @falcon.before(header_hook)
    @falcon.before(_another_fish.hook)
    @falcon.before(header_hook)
    def on_delete_collection(self, req, resp, fish):
        if fish != 'wet':
            raise falcon.HTTPUnavailableForLegalReasons('fish must be wet')
        self._items = {}
        resp.status = falcon.HTTP_NO_CONTENT

    @falcon.before(_another_fish)
    def on_get(self, req, resp, fish, itemid):
        resp.set_header('X-Fish-Trait', fish)
        resp.media = self._items[itemid]

    def on_get_collection(self, req, resp):
        resp.media = sorted(self._items.values(),
                            key=lambda item: item['itemid'])

    def on_head_(self):
        return 'I shall not be decorated.'

    def on_header(self):
        return 'I shall not be decorated.'

    def on_post_collection(self, req, resp):
        self._sequence += 1
        itemid = self._sequence
        self._items[itemid] = dict(req.media, itemid=itemid)
        resp.location = '/items/{}'.format(itemid)
        resp.status = falcon.HTTP_CREATED


@pytest.fixture
def app_client():
    items = PiggybackingCollection()

    app = falcon.API()
    app.add_route('/items', items, suffix='collection')
    app.add_route('/items/{itemid:int}', items)

    return testing.TestClient(app)


def test_piggybacking_resource_post_item(app_client):
    resp1 = app_client.simulate_post('/items', json={'color': 'green'})
    assert resp1.status_code == 201
    assert 'X-Fish-Trait' not in resp1.headers
    assert resp1.headers['Location'] == '/items/1'
    assert resp1.headers['X-Hook-Applied'] == '1'

    resp2 = app_client.simulate_get(resp1.headers['Location'])
    assert resp2.status_code == 200
    assert resp2.headers['X-Fish-Trait'] == 'slippery'
    assert resp2.headers['X-Hook-Applied'] == '1'
    assert resp2.json == {'color': 'green', 'itemid': 1}

    resp3 = app_client.simulate_get('/items')
    assert resp3.status_code == 200
    assert 'X-Fish-Trait' not in resp3.headers
    assert resp3.headers['X-Hook-Applied'] == '1'
    assert resp3.json == [{'color': 'green', 'itemid': 1}]


def test_piggybacking_resource_post_and_delete(app_client):
    for number in range(1, 8):
        resp = app_client.simulate_post('/items', json={'number': number})
        assert resp.status_code == 201
        assert resp.headers['X-Hook-Applied'] == '1'

        assert len(app_client.simulate_get('/items').json) == number

    resp = app_client.simulate_delete('/items/7'.format(number))
    assert resp.status_code == 204
    assert resp.headers['X-Fish-Trait'] == 'wet'
    assert resp.headers['X-Hook-Applied'] == '1'
    assert len(app_client.simulate_get('/items').json) == 6

    resp = app_client.simulate_delete('/items')
    assert resp.status_code == 204
    assert resp.headers['X-Hook-Applied'] == '3'
    assert app_client.simulate_get('/items').json == []


def test_decorable_name_pattern():
    resource = PiggybackingCollection()
    assert resource.on_head_() == 'I shall not be decorated.'
    assert resource.on_header() == 'I shall not be decorated.'
