# -*- coding: utf-8 -*-

import io

import pytest

import falcon
from falcon.request import Request
from falcon.response import Response
from falcon.routing import StaticRoute
import falcon.testing as testing


@pytest.fixture
def client():
    app = falcon.API()
    return testing.TestClient(app)


@pytest.mark.parametrize('uri', [
    # Root
    '/static',
    '/static/',
    '/static/.',

    # Attempt to jump out of the directory
    '/static/..',
    '/static/../.',
    '/static/.././etc/passwd',
    '/static/../etc/passwd',
    '/static/css/../../secret',
    '/static/css/../../etc/passwd',
    '/static/./../etc/passwd',

    # The file system probably won't process escapes, but better safe than sorry
    '/static/css/../.\\056/etc/passwd',
    '/static/./\\056./etc/passwd',
    '/static/\\056\\056/etc/passwd',

    # Double slash
    '/static//test.css',
    '/static//COM10',
    '/static/path//test.css',
    '/static/path///test.css',
    '/static/path////test.css',
    '/static/path/foo//test.css',

    # Control characters (0x00–0x1f and 0x80–0x9f)
    '/static/.\x00ssh/authorized_keys',
    '/static/.\x1fssh/authorized_keys',
    '/static/.\x80ssh/authorized_keys',
    '/static/.\x9fssh/authorized_keys',

    # Reserved characters (~, ?, <, >, :, *, |, ', and ")
    '/static/~/.ssh/authorized_keys',
    '/static/.ssh/authorized_key?',
    '/static/.ssh/authorized_key>foo',
    '/static/.ssh/authorized_key|foo',
    '/static/.ssh/authorized_key<foo',
    '/static/something:something',
    '/static/thing*.sql',
    '/static/\'thing\'.sql',
    '/static/"thing".sql',

    # Trailing periods and spaces
    '/static/something.',
    '/static/something..',
    '/static/something ',
    '/static/ something ',
    '/static/ something ',
    '/static/something\t',
    '/static/\tsomething',

    # Too long
    '/static/' + ('t' * StaticRoute._MAX_NON_PREFIXED_LEN) + 'x',

])
def test_bad_path(uri, monkeypatch):
    monkeypatch.setattr(io, 'open', lambda path, mode: path)

    sr = StaticRoute('/static', '/var/www/statics')

    req = Request(testing.create_environ(
        host='test.com',
        path=uri,
        app='statics'
    ))

    resp = Response()

    with pytest.raises(falcon.HTTPNotFound):
        sr(req, resp)


@pytest.mark.parametrize('prefix, directory', [
    ('static', '/var/www/statics'),
    ('/static', './var/www/statics'),
    ('/static', 'statics'),
    ('/static', '../statics'),
])
def test_invalid_args(prefix, directory, client):
    with pytest.raises(ValueError):
        StaticRoute(prefix, directory)

    with pytest.raises(ValueError):
        client.app.add_static_route(prefix, directory)


@pytest.mark.parametrize('uri_prefix, uri_path, expected_path, mtype', [
    ('/static/', '/css/test.css', '/css/test.css', 'text/css'),
    ('/static', '/css/test.css', '/css/test.css', 'text/css'),
    (
        '/static',
        '/' + ('t' * StaticRoute._MAX_NON_PREFIXED_LEN),
        '/' + ('t' * StaticRoute._MAX_NON_PREFIXED_LEN),
        'application/octet-stream',
    ),
    ('/static', '/.test.css', '/.test.css', 'text/css'),
    ('/some/download/', '/report.pdf', '/report.pdf', 'application/pdf'),
    ('/some/download/', '/Fancy Report.pdf', '/Fancy Report.pdf', 'application/pdf'),
    ('/some/download', '/report.zip', '/report.zip', 'application/zip'),
    ('/some/download', '/foo/../report.zip', '/report.zip', 'application/zip'),
    ('/some/download', '/foo/../bar/../report.zip', '/report.zip', 'application/zip'),
    ('/some/download', '/foo/bar/../../report.zip', '/report.zip', 'application/zip'),
])
def test_good_path(uri_prefix, uri_path, expected_path, mtype, monkeypatch):
    monkeypatch.setattr(io, 'open', lambda path, mode: path)

    sr = StaticRoute(uri_prefix, '/var/www/statics')

    req_path = uri_prefix[:-1] if uri_prefix.endswith('/') else uri_prefix
    req_path += uri_path

    req = Request(testing.create_environ(
        host='test.com',
        path=req_path,
        app='statics'
    ))

    resp = Response()

    sr(req, resp)

    assert resp.content_type == mtype
    assert resp.stream == '/var/www/statics' + expected_path


def test_lifo(client, monkeypatch):
    monkeypatch.setattr(io, 'open', lambda path, mode: [path.encode('utf-8')])

    client.app.add_static_route('/downloads', '/opt/somesite/downloads')
    client.app.add_static_route('/downloads/archive', '/opt/somesite/x')

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == '/opt/somesite/downloads/thing.zip'

    response = client.simulate_request(path='/downloads/archive/thingtoo.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == '/opt/somesite/x/thingtoo.zip'


def test_lifo_negative(client, monkeypatch):
    monkeypatch.setattr(io, 'open', lambda path, mode: [path.encode('utf-8')])

    client.app.add_static_route('/downloads/archive', '/opt/somesite/x')
    client.app.add_static_route('/downloads', '/opt/somesite/downloads')

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == '/opt/somesite/downloads/thing.zip'

    response = client.simulate_request(path='/downloads/archive/thingtoo.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == '/opt/somesite/downloads/archive/thingtoo.zip'


def test_downloadable(client, monkeypatch):
    monkeypatch.setattr(io, 'open', lambda path, mode: [path.encode('utf-8')])

    client.app.add_static_route('/downloads', '/opt/somesite/downloads', downloadable=True)
    client.app.add_static_route('/assets/', '/opt/somesite/assets')

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_200
    assert response.headers['Content-Disposition'] == 'attachment; filename="thing.zip"'

    response = client.simulate_request(path='/downloads/Some Report.zip')
    assert response.status == falcon.HTTP_200
    assert response.headers['Content-Disposition'] == 'attachment; filename="Some Report.zip"'

    response = client.simulate_request(path='/assets/css/main.css')
    assert response.status == falcon.HTTP_200
    assert 'Content-Disposition' not in response.headers


def test_downloadable_not_found(client):
    client.app.add_static_route('/downloads', '/opt/somesite/downloads', downloadable=True)

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_404
