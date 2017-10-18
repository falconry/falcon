import os

from falcon.request import Request
from falcon.response import Response
from falcon.statics import Statics
import falcon.testing as testing


class MockStatics(Statics):

    def _get_stream(self, path):
        return path


def test_serve_static_file():
    static = MockStatics('/static', '/var/www/statics')

    req = Request(testing.create_environ(
        host='test.com',
        path='/static/../css//test.css',
        app='statics'
    ))
    resp = Response()

    static(req, resp)

    assert resp.content_type == 'text/css'
    assert resp.stream == '/var/www/statics/css/test.css'

