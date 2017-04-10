"""Application tests for URI templates using simulate_get().

These tests differ from those in test_default_router in that they are
a collection of sanity-checks that exercise the full framework code
path via simulate_get(), vs. probing the router directly.
"""

import pytest
import six

import falcon
from falcon import testing


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


@pytest.mark.skipif(six.PY3, reason='Test only applies to Python 2')
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
    template = '/widgets/{{{0}}}'.format(field_name)

    client.app.add_route(template, resource)

    client.simulate_get('/widgets/123')
    assert resource.called
    assert resource.captured_kwargs[field_name] == '123'


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
    assert result.status == falcon.HTTP_200
    assert resource2.called
    assert resource2.id == '123'
    assert resource2.req.path == '/2/123'

    resource3 = IDResource()
    client.app.add_route('/3/{id}', resource3)
    result = client.simulate_get('/3/123/')
    assert result.status == falcon.HTTP_200
    assert resource3.called
    assert resource3.id == '123'
    assert resource3.req.path == '/3/123'


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
