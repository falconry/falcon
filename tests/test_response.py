import falcon
from falcon import MEDIA_TEXT


def test_response_set_content_type_set():
    resp = falcon.Response()
    resp._set_media_type(MEDIA_TEXT)
    assert resp._headers['content-type'] == MEDIA_TEXT


def test_response_set_content_type_not_set():
    resp = falcon.Response()
    assert 'content-type' not in resp._headers
