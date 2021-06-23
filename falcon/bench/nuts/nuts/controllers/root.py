import random

import pecan
from pecan import expose, response, request


_body = pecan.x_test_body
_headers = pecan.x_test_headers


class TestController:
    def __init__(self, account_id):
        self.account_id = account_id

    @expose(content_type='text/plain')
    def test(self):
        user_agent = request.headers['User-Agent']  # NOQA
        limit = request.params.get('limit', '10')  # NOQA
        response.headers.update(_headers)

        return _body


class HelloController:
    @expose()
    def _lookup(self, account_id, *remainder):
        return TestController(account_id), remainder


class RootController:
    @expose(content_type='text/plain')
    def index(self):
        response.headers.update(_headers)
        return _body

    hello = HelloController()
