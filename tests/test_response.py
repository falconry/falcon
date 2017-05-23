import falcon
import falcon.testing as testing
from falcon import DEFAULT_MEDIA_TYPE, MEDIA_TEXT


def test_response_set_content_type():
    resp = falcon.Response()
    resp.set_media_type(MEDIA_TEXT)
    assert resp._headers["content-type"] == MEDIA_TEXT