import pytest

import falcon
import falcon.asgi
import falcon.testing as testing


class TestSlots:
    def test_slots_request(self, asgi):
        req = testing.create_asgi_req() if asgi else testing.create_req()

        try:
            req.doesnt = 'exist'
        except AttributeError:
            pytest.fail('Unable to add additional variables dynamically')

    def test_slots_response(self, asgi):
        if asgi:
            resp = falcon.asgi.Response()
        else:
            resp = falcon.Response()

        try:
            resp.doesnt = 'exist'
        except AttributeError:
            pytest.fail('Unable to add additional variables dynamically')
