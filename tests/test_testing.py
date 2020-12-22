import pytest

import falcon
from falcon import App, status_codes, testing


class CustomCookies:
    def items(self):
        return [('foo', 'bar'), ('baz', 'foo')]


def another_dummy_wsgi_app(environ, start_response):
    start_response(status_codes.HTTP_OK, [('Content-Type', 'text/plain')])

    yield b'It works!'


def test_testing_client_handles_wsgi_generator_app():
    client = testing.TestClient(another_dummy_wsgi_app)

    response = client.simulate_get('/nevermind')

    assert response.status == status_codes.HTTP_OK
    assert response.text == 'It works!'


@pytest.mark.parametrize('items', [
    (),
    (b'1',),
    (b'1', b'2'),
    (b'Hello, ', b'World', b'!\n'),
])
def test_closed_wsgi_iterable(items):
    assert tuple(testing.closed_wsgi_iterable(items)) == items


@pytest.mark.parametrize('version, valid', [
    ('1', True),
    ('1.0', True),
    ('1.1', True),
    ('2', True),
    ('2.0', True),
    ('', False),
    ('0', False),
    ('1.2', False),
    ('2.1', False),
    ('3', False),
    ('3.1', False),
    ('11', False),
    ('22', False),
])
def test_simulate_request_http_version(version, valid):
    app = App()

    if valid:
        testing.simulate_request(app, http_version=version)
    else:
        with pytest.raises(ValueError):
            testing.simulate_request(app, http_version=version)


def test_simulate_request_content_type():
    class Foo:
        def on_post(self, req, resp):
            resp.text = req.content_type

    app = App()
    app.add_route('/', Foo())

    headers = {'Content-Type': falcon.MEDIA_TEXT}

    result = testing.simulate_post(app, '/', headers=headers)
    assert result.text == falcon.MEDIA_TEXT

    result = testing.simulate_post(app, '/', content_type=falcon.MEDIA_HTML)
    assert result.text == falcon.MEDIA_HTML

    result = testing.simulate_post(app, '/', content_type=falcon.MEDIA_HTML, headers=headers)
    assert result.text == falcon.MEDIA_HTML

    result = testing.simulate_post(app, '/', json={})
    assert result.text == falcon.MEDIA_JSON

    result = testing.simulate_post(app, '/', json={}, content_type=falcon.MEDIA_HTML)
    assert result.text == falcon.MEDIA_JSON

    result = testing.simulate_post(app, '/', json={}, headers=headers)
    assert result.text == falcon.MEDIA_JSON

    result = testing.simulate_post(
        app, '/', json={}, headers=headers, content_type=falcon.MEDIA_HTML)
    assert result.text == falcon.MEDIA_JSON


@pytest.mark.parametrize('cookies', [
    {'foo': 'bar', 'baz': 'foo'},
    CustomCookies()
])
def test_create_environ_cookies(cookies):
    environ = testing.create_environ(cookies=cookies)

    assert environ['HTTP_COOKIE'] in ('foo=bar; baz=foo', 'baz=foo; foo=bar')


def test_create_environ_cookies_options_method():
    environ = testing.create_environ(method='OPTIONS', cookies={'foo': 'bar'})

    assert 'HTTP_COOKIE' not in environ


def test_cookies_jar():
    class Foo:
        def on_get(self, req, resp):
            # NOTE(myusko): In the future we shouldn't change the cookie
            #             a test depends on the input.
            # NOTE(kgriffs): This is the only test that uses a single
            #   cookie (vs. multiple) as input; if this input ever changes,
            #   a separate test will need to be added to explicitly verify
            #   this use case.
            resp.set_cookie('has_permission', 'true')

        def on_post(self, req, resp):
            if req.cookies['has_permission'] == 'true':
                resp.status = falcon.HTTP_200
            else:
                resp.status = falcon.HTTP_403

    app = App()
    app.add_route('/jars', Foo())

    client = testing.TestClient(app)

    response_one = client.simulate_get('/jars')
    response_two = client.simulate_post('/jars', cookies=response_one.cookies)

    assert response_two.status == falcon.HTTP_200


def test_create_environ_default_ua():
    default_ua = 'falcon-client/' + falcon.__version__

    environ = testing.create_environ()
    assert environ['HTTP_USER_AGENT'] == default_ua

    req = falcon.request.Request(environ)
    assert req.user_agent == default_ua


def test_create_environ_default_ua_override():
    ua = 'curl/7.64.1'

    environ = testing.create_environ(headers={'user-agent': ua})
    assert environ['HTTP_USER_AGENT'] == ua

    req = falcon.request.Request(environ)
    assert req.user_agent == ua


def test_missing_header_is_none():
    req = testing.create_req()
    assert req.auth is None
