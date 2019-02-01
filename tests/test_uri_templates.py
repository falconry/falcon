"""Application tests for URI templates using simulate_get().

These tests differ from those in test_default_router in that they are
a collection of sanity-checks that exercise the full framework code
path via simulate_get(), vs. probing the router directly.
"""

from datetime import datetime
import uuid

import pytest

import falcon
from falcon import testing
from falcon.routing.util import SuffixedMethodNotFoundError
from falcon.util import compat


_TEST_UUID = uuid.uuid4()
_TEST_UUID_2 = uuid.uuid4()
_TEST_UUID_STR = str(_TEST_UUID)
_TEST_UUID_STR_2 = str(_TEST_UUID_2)
_TEST_UUID_STR_SANS_HYPHENS = _TEST_UUID_STR.replace('-', '')


class IDResource(object):
    def __init__(self):
        self.id = None
        self.name = None
        self.called = False

    def on_get(self, req, resp, id):
        self.id = id
        self.called = True
        self.req = req


class NameResource(object):
    def __init__(self):
        self.id = None
        self.name = None
        self.called = False

    def on_get(self, req, resp, id, name):
        self.id = id
        self.name = name
        self.called = True


class NameAndDigitResource(object):
    def __init__(self):
        self.id = None
        self.name51 = None
        self.called = False

    def on_get(self, req, resp, id, name51):
        self.id = id
        self.name51 = name51
        self.called = True


class FileResource(object):
    def __init__(self):
        self.file_id = None
        self.called = False

    def on_get(self, req, resp, file_id):
        self.file_id = file_id
        self.called = True


class FileDetailsResource(object):
    def __init__(self):
        self.file_id = None
        self.ext = None
        self.called = False

    def on_get(self, req, resp, file_id, ext):
        self.file_id = file_id
        self.ext = ext
        self.called = True


class ResourceWithSuffixRoutes(object):
    def __init__(self):
        self.get_called = False
        self.post_called = False
        self.put_called = False

    def on_get(self, req, resp, collection_id, item_id):
        self.collection_id = collection_id
        self.item_id = item_id
        self.get_called = True

    def on_post(self, req, resp, collection_id, item_id):
        self.collection_id = collection_id
        self.item_id = item_id
        self.post_called = True

    def on_put(self, req, resp, collection_id, item_id):
        self.collection_id = collection_id
        self.item_id = item_id
        self.put_called = True

    def on_get_collection(self, req, resp, collection_id):
        self.collection_id = collection_id
        self.get_called = True

    def on_post_collection(self, req, resp, collection_id):
        self.collection_id = collection_id
        self.post_called = True

    def on_put_collection(self, req, resp, collection_id):
        self.collection_id = collection_id
        self.put_called = True


@pytest.fixture
def resource():
    return testing.SimpleTestResource()


@pytest.fixture
def client():
    return testing.TestClient(falcon.API())


def test_root_path(client, resource):
    client.app.add_route('/', resource)
    client.simulate_get('/')
    assert resource.called


def test_no_vars(client, resource):
    client.app.add_route('/hello/world', resource)
    client.simulate_get('/hello/world')
    assert resource.called


@pytest.mark.skipif(compat.PY3, reason='Test only applies to Python 2')
def test_unicode_literal_routes(client, resource):
    client.app.add_route(u'/hello/world', resource)
    client.simulate_get('/hello/world')
    assert resource.called


def test_special_chars(client, resource):
    client.app.add_route('/hello/world.json', resource)
    client.app.add_route('/hello(world)', resource)

    client.simulate_get('/hello/world_json')
    assert not resource.called

    client.simulate_get('/helloworld')
    assert not resource.called

    client.simulate_get('/hello/world.json')
    assert resource.called

    client.simulate_get('/hello(world)')
    assert resource.called


@pytest.mark.parametrize('field_name', [
    'id',
    'id123',
    'widget_id',
])
def test_single(client, resource, field_name):
    template = '/widgets/{{{}}}'.format(field_name)

    client.app.add_route(template, resource)

    client.simulate_get('/widgets/123')
    assert resource.called
    assert resource.captured_kwargs[field_name] == '123'


@pytest.mark.parametrize('uri_template,', [
    '/{id:int}',
    '/{id:int(3)}',
    '/{id:int(min=123)}',
    '/{id:int(min=123, max=123)}',
])
def test_int_converter(client, uri_template):
    resource1 = IDResource()
    client.app.add_route(uri_template, resource1)

    result = client.simulate_get('/123')

    assert result.status_code == 200
    assert resource1.called
    assert resource1.id == 123
    assert resource1.req.path == '/123'


@pytest.mark.parametrize('uri_template,', [
    '/{id:int(2)}',
    '/{id:int(min=124)}',
    '/{id:int(num_digits=3, max=100)}',
])
def test_int_converter_rejections(client, uri_template):
    resource1 = IDResource()
    client.app.add_route(uri_template, resource1)

    result = client.simulate_get('/123')

    assert result.status_code == 404
    assert not resource1.called


@pytest.mark.parametrize('uri_template, path, dt_expected', [
    (
        '/{start_year:int}-to-{timestamp:dt}',
        '/1961-to-1969-07-21T02:56:00Z',
        datetime(1969, 7, 21, 2, 56, 0)
    ),
    (
        '/{start_year:int}-to-{timestamp:dt("%Y-%m-%d")}',
        '/1961-to-1969-07-21',
        datetime(1969, 7, 21)
    ),
    (
        '/{start_year:int}/{timestamp:dt("%Y-%m-%d %H:%M")}',
        '/1961/1969-07-21 14:30',
        datetime(1969, 7, 21, 14, 30)
    ),
    (
        '/{start_year:int}-to-{timestamp:dt("%Y-%m")}',
        '/1961-to-1969-07-21',
        None
    ),
])
def test_datetime_converter(client, resource, uri_template, path, dt_expected):
    client.app.add_route(uri_template, resource)

    result = client.simulate_get(path)

    if dt_expected is None:
        assert result.status_code == 404
        assert not resource.called
    else:
        assert result.status_code == 200
        assert resource.called
        assert resource.captured_kwargs['start_year'] == 1961
        assert resource.captured_kwargs['timestamp'] == dt_expected


@pytest.mark.parametrize('uri_template, path, expected', [
    (
        '/widgets/{widget_id:uuid}',
        '/widgets/' + _TEST_UUID_STR,
        {'widget_id': _TEST_UUID}
    ),
    (
        '/widgets/{widget_id:uuid}/orders',
        '/widgets/' + _TEST_UUID_STR_SANS_HYPHENS + '/orders',
        {'widget_id': _TEST_UUID}
    ),
    (
        '/versions/diff/{left:uuid()}...{right:uuid()}',
        '/versions/diff/{}...{}'.format(_TEST_UUID_STR, _TEST_UUID_STR_2),
        {'left': _TEST_UUID, 'right': _TEST_UUID_2, }
    ),
    (
        '/versions/diff/{left:uuid}...{right:uuid()}',
        '/versions/diff/{}...{}'.format(_TEST_UUID_STR, _TEST_UUID_STR_2),
        {'left': _TEST_UUID, 'right': _TEST_UUID_2, }
    ),
    (
        '/versions/diff/{left:uuid()}...{right:uuid}',
        '/versions/diff/{}...{}'.format(_TEST_UUID_STR, _TEST_UUID_STR_2),
        {'left': _TEST_UUID, 'right': _TEST_UUID_2, }
    ),
    (
        '/widgets/{widget_id:uuid}/orders',
        '/widgets/' + _TEST_UUID_STR_SANS_HYPHENS[:-1] + '/orders',
        None
    ),
])
def test_uuid_converter(client, resource, uri_template, path, expected):
    client.app.add_route(uri_template, resource)

    result = client.simulate_get(path)

    if expected is None:
        assert result.status_code == 404
        assert not resource.called
    else:
        assert result.status_code == 200
        assert resource.called
        assert resource.captured_kwargs == expected


def test_uuid_converter_complex_segment(client, resource):
    client.app.add_route('/pages/{first:uuid}...{last:uuid}', resource)

    first_uuid = uuid.uuid4()
    last_uuid = uuid.uuid4()

    result = client.simulate_get('/pages/{}...{}'.format(
        first_uuid,
        last_uuid
    ))

    assert result.status_code == 200
    assert resource.called
    assert resource.captured_kwargs['first'] == first_uuid
    assert resource.captured_kwargs['last'] == last_uuid


@pytest.mark.parametrize('uri_template, path, expected', [
    (
        '/{food:spam}',
        '/something',
        {'food': 'spam!'}
    ),
    (
        '/{food:spam(")")}:{food_too:spam("()")}',
        '/bacon:eggs',
        {'food': 'spam!', 'food_too': 'spam!'}
    ),
    (
        '/({food:spam()}){food_too:spam("()")}',
        '/(bacon)eggs',
        {'food': 'spam!', 'food_too': 'spam!'}
    ),
])
def test_converter_custom(client, resource, uri_template, path, expected):
    class SpamConverter(object):
        def __init__(self, useless_text=None):
            pass

        def convert(self, fragment):
            return 'spam!'

    client.app.router_options.converters['spam'] = SpamConverter
    client.app.add_route(uri_template, resource)

    result = client.simulate_get(path)

    assert result.status_code == 200
    assert resource.called
    assert resource.captured_kwargs == expected


def test_single_trailing_slash(client):
    resource1 = IDResource()
    client.app.add_route('/1/{id}/', resource1)
    result = client.simulate_get('/1/123')
    assert result.status == falcon.HTTP_200
    assert resource1.called
    assert resource1.id == '123'
    assert resource1.req.path == '/1/123'

    resource2 = IDResource()
    client.app.add_route('/2/{id}/', resource2)
    result = client.simulate_get('/2/123/')
    assert result.status == falcon.HTTP_404
    assert not resource2.called
    assert resource2.id is None

    resource3 = IDResource()
    client.app.add_route('/3/{id}/', resource3)
    client.app.req_options.strip_url_path_trailing_slash = True
    result = client.simulate_get('/3/123/')
    assert result.status == falcon.HTTP_200
    assert resource3.called
    assert resource3.id == '123'
    assert resource3.req.path == '/3/123'

    resource4 = IDResource()
    client.app.add_route('/4/{id}', resource4)
    client.app.req_options.strip_url_path_trailing_slash = False
    result = client.simulate_get('/4/123/')
    assert result.status == falcon.HTTP_404
    assert not resource4.called
    assert resource4.id is None


def test_multiple(client):
    resource = NameResource()
    client.app.add_route('/messages/{id}/names/{name}', resource)

    test_id = 'bfb54d43-219b-4336-a623-6172f920592e'
    test_name = '758e3922-dd6d-4007-a589-50fba0789365'
    path = '/messages/' + test_id + '/names/' + test_name
    client.simulate_get(path)

    assert resource.called
    assert resource.id == test_id
    assert resource.name == test_name


@pytest.mark.parametrize('uri_template', [
    '//',
    '//begin',
    '/end//',
    '/in//side',
])
def test_empty_path_component(client, resource, uri_template):
    with pytest.raises(ValueError):
        client.app.add_route(uri_template, resource)


@pytest.mark.parametrize('uri_template', [
    '',
    'no',
    'no/leading_slash',
])
def test_relative_path(client, resource, uri_template):
    with pytest.raises(ValueError):
        client.app.add_route(uri_template, resource)


@pytest.mark.parametrize('reverse', [True, False])
def test_same_level_complex_var(client, reverse):
    file_resource = FileResource()
    details_resource = FileDetailsResource()

    routes = [
        ('/files/{file_id}', file_resource),
        ('/files/{file_id}.{ext}', details_resource)
    ]
    if reverse:
        routes.reverse()

    for uri_template, resource in routes:
        client.app.add_route(uri_template, resource)

    file_id_1 = 'bc6b201d-b449-4290-a061-8eeb9f7b1450'
    file_id_2 = '33b7f34c-6ee6-40e6-89a3-742a69b59de0'
    ext = 'a4581b95-bc36-4c08-a3c2-23ba266abdf2'
    path_1 = '/files/' + file_id_1
    path_2 = '/files/' + file_id_2 + '.' + ext

    client.simulate_get(path_1)
    assert file_resource.called
    assert file_resource.file_id == file_id_1

    client.simulate_get(path_2)
    assert details_resource.called
    assert details_resource.file_id == file_id_2
    assert details_resource.ext == ext


def test_adding_suffix_routes(client):
    resource_with_suffix_routes = ResourceWithSuffixRoutes()
    client.app.add_route(
        '/collections/{collection_id}/items/{item_id}', resource_with_suffix_routes)
    client.app.add_route(
        '/collections/{collection_id}/items', resource_with_suffix_routes, suffix='collection')
    # GET
    client.simulate_get('/collections/123/items/456')
    assert resource_with_suffix_routes.collection_id == '123'
    assert resource_with_suffix_routes.item_id == '456'
    assert resource_with_suffix_routes.get_called
    client.simulate_get('/collections/foo/items')
    assert resource_with_suffix_routes.collection_id == 'foo'
    # POST
    client.simulate_post('/collections/foo234/items/foo456')
    assert resource_with_suffix_routes.collection_id == 'foo234'
    assert resource_with_suffix_routes.item_id == 'foo456'
    assert resource_with_suffix_routes.post_called
    client.simulate_post('/collections/foo123/items')
    assert resource_with_suffix_routes.collection_id == 'foo123'
    # PUT
    client.simulate_put('/collections/foo345/items/foo567')
    assert resource_with_suffix_routes.collection_id == 'foo345'
    assert resource_with_suffix_routes.item_id == 'foo567'
    assert resource_with_suffix_routes.put_called
    client.simulate_put('/collections/foo321/items')
    assert resource_with_suffix_routes.collection_id == 'foo321'


def test_custom_error_on_suffix_route_not_found(client):
    resource_with_suffix_routes = ResourceWithSuffixRoutes()
    with pytest.raises(SuffixedMethodNotFoundError):
        client.app.add_route(
            '/collections/{collection_id}/items', resource_with_suffix_routes, suffix='bad-alt')
