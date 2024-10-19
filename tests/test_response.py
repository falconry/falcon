from io import BytesIO
from unittest.mock import MagicMock

import pytest

from falcon import MEDIA_TEXT
from falcon import ResponseOptions
from falcon.util.deprecation import AttributeRemovedError


@pytest.fixture()
def resp(asgi, util):
    return util.create_resp(asgi)


def test_response_set_content_type_set(resp):
    resp._set_media_type(MEDIA_TEXT)
    assert resp._headers['content-type'] == MEDIA_TEXT


def test_response_set_content_type_not_set(resp):
    assert 'content-type' not in resp._headers

    resp._set_media_type()
    assert 'content-type' not in resp._headers


def test_response_get_headers(resp):
    resp.append_header('x-things1', 'thing-1')
    resp.append_header('x-things2', 'thing-2')
    resp.append_header('X-Things3', 'Thing-3')

    resp.set_cookie('Chocolate', 'Chip')

    headers = resp.headers
    assert headers['x-things1'] == 'thing-1'
    assert headers['x-things2'] == 'thing-2'
    assert headers['x-things3'] == 'Thing-3'

    assert 'set-cookie' not in headers


def test_add_link_removed(resp):
    # NOTE(kgriffs): Ensure AttributeRemovedError inherits from AttributeError
    for exc_type in (AttributeError, AttributeRemovedError):
        with pytest.raises(exc_type):
            resp.add_link('/things/1337', 'next')


def test_body_removed(resp):
    # NOTE(kgriffs): Ensure AttributeRemovedError inherits from AttributeError
    for exc_type in (AttributeError, AttributeRemovedError):
        with pytest.raises(exc_type):
            resp.body = '{"message": "Hello, World!"}'

    for exc_type in (AttributeError, AttributeRemovedError):
        with pytest.raises(exc_type):
            resp.body


def test_response_attempt_to_set_read_only_headers(resp):
    resp.append_header('x-things1', 'thing-1')
    resp.append_header('x-things2', 'thing-2')
    resp.append_header('x-things3', 'thing-3a')
    resp.append_header('X-Things3', 'thing-3b')

    with pytest.raises(AttributeError):
        resp.headers = {'x-things4': 'thing-4'}

    headers = resp.headers
    assert headers['x-things1'] == 'thing-1'
    assert headers['x-things2'] == 'thing-2'
    assert headers['x-things3'] == 'thing-3a, thing-3b'


def test_response_option_mimetype_init(monkeypatch):
    mock = MagicMock()
    mock.inited = False
    mock.types_map = {'.js': 'application/javascript'}
    monkeypatch.setattr('falcon.response.mimetypes', mock)

    ro = ResponseOptions()

    assert ro.static_media_types['.js'] == 'text/javascript'
    assert ro.static_media_types['.json'] == 'application/json'
    assert ro.static_media_types['.mjs'] == 'text/javascript'

    mock.reset_mock()
    mock.inited = True
    ro = ResponseOptions()
    mock.init.assert_not_called()

    assert ro.static_media_types['.js'] == 'text/javascript'
    assert ro.static_media_types['.json'] == 'application/json'
    assert ro.static_media_types['.mjs'] == 'text/javascript'


@pytest.mark.parametrize('content', [b'', b'dummy content'])
def test_response_set_stream(resp, content):
    stream = BytesIO(content)
    content_length = len(content)

    resp.set_stream(stream, content_length)

    assert resp.stream is stream
    assert resp.headers['content-length'] == str(content_length)
