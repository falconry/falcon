import time

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


def test_asgi_request_event_emitter_hang():
    # NOTE(kgriffs): This tests the ASGI server behavior that
    #   ASGIRequestEventEmitter simulates when emit() is called
    #   again after there are not more events available.

    expected_elasped_min = 1
    disconnect_at = time.time() + expected_elasped_min

    emit = testing.ASGIRequestEventEmitter(disconnect_at=disconnect_at)

    async def t():
        start = time.time()
        while True:
            event = await emit()
            if not event.get('more_body', False):
                break
        elapsed = time.time() - start

        assert elapsed < 0.1

        start = time.time()
        await emit()
        elapsed = time.time() - start

        assert (elapsed + 0.1) > expected_elasped_min

    falcon.invoke_coroutine_sync(t)


def test_ignore_extra_asgi_events():
    collect = testing.ASGIResponseEventCollector()

    async def t():
        await collect({'type': 'http.response.start', 'status': 200})
        await collect({'type': 'http.response.body', 'more_body': False})

        # NOTE(kgriffs): Events after more_body is False are ignored to conform
        #   to the ASGI spec.
        await collect({'type': 'http.response.body'})
        assert len(collect.events) == 2

    falcon.invoke_coroutine_sync(t)


def test_invalid_asgi_events():
    collect = testing.ASGIResponseEventCollector()

    def make_event(headers=None, status=200):
        return {
            'type': 'http.response.start',
            'headers': headers or [],
            'status': status
        }

    async def t():
        with pytest.raises(TypeError):
            await collect({'type': 123})

        with pytest.raises(TypeError):
            headers = [
                ('notbytes', b'bytes')
            ]
            await collect(make_event(headers))

        with pytest.raises(TypeError):
            headers = [
                (b'bytes', 'notbytes')
            ]
            await collect(make_event(headers))

        with pytest.raises(ValueError):
            headers = [
                # NOTE(kgriffs): Name must be lowercase
                (b'Content-Type', b'application/json')
            ]
            await collect(make_event(headers))

        with pytest.raises(TypeError):
            await collect(make_event(status='200'))

        with pytest.raises(TypeError):
            await collect(make_event(status=200.1))

        with pytest.raises(TypeError):
            await collect({'type': 'http.response.body', 'body': 'notbytes'})

        with pytest.raises(TypeError):
            await collect({'type': 'http.response.body', 'more_body': ''})

        with pytest.raises(ValueError):
            # NOTE(kgriffs): Invalid type
            await collect({'type': 'http.response.bod'})

    falcon.invoke_coroutine_sync(t)


def test_is_asgi_app_cls():
    class Foo:
        @classmethod
        def class_meth(cls, scope, receive, send):
            pass

    assert testing.client._is_asgi_app(Foo.class_meth)


def test_simulate_request_content_type():
    class Foo:
        def on_post(self, req, resp):
            resp.body = req.content_type

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
            # NOTE(myuz): In the future we shouldn't change the cookie
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
