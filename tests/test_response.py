import pytest

import falcon
from falcon import MEDIA_TEXT


def test_response_set_content_type_set():
    resp = falcon.Response()
    resp._set_media_type(MEDIA_TEXT)
    assert resp._headers['content-type'] == MEDIA_TEXT


def test_response_set_content_type_not_set():
    resp = falcon.Response()
    assert 'content-type' not in resp._headers


def test_response_get_headers():
    resp = falcon.Response()
    resp.append_header('x-things1', 'thing-1')
    resp.append_header('x-things2', 'thing-2')
    resp.append_header('x-things3', 'thing-3')

    headers = resp.headers
    assert 'x-things1' in headers
    assert 'x-things2' in headers
    assert 'x-things3' in headers


def test_response_attempt_to_set_read_only_headers():
    resp = falcon.Response()

    with pytest.raises(AttributeError):
        resp.headers = ['x-things1', 'x-things2', 'x-things3']
