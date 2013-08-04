import falcon
import falcon.testing as testing


class Thinger(object):
    def __init__(self, number):
        pass


def teh_wrapper(req, resp, params):
    pass


class TypeErrornator(object):

    def on_get(self, req, resp):
        silly = True

        # Call an uncallable
        return silly()

    def on_head(self, req, resp):
        # Call with wrong number of arguments
        Thinger()

    def on_put(self, number):
        # Responder has incorrect args
        pass

    def on_post(self, req, resp, user_id):
        # Responder has incorrect args
        Thinger()


class TestTypeError(testing.TestBase):

    def before(self):
        self.api = falcon.API(before=teh_wrapper)
        self.api.add_route('/typeerror', TypeErrornator())
        self.api.add_route('/{user_id}/thingy', TypeErrornator())

    def test_not_callable(self):
        self.simulate_request('/typeerror')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_not_enough_init_args(self):
        self.simulate_request('/typeerror', method='HEAD')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_responder_incorrect_argspec(self):
        self.simulate_request('/typeerror', method='PUT')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_wrapped_not_enough_init_args(self):
        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_double_wrapped_not_enough_init_args(self):
        self.api = falcon.API(before=[teh_wrapper, teh_wrapper])
        self.api.add_route('/typeerror', TypeErrornator())
        self.api.add_route('/{user_id}/thingy', TypeErrornator())

        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_triple_wrapped_not_enough_init_args(self):
        self.api = falcon.API(before=[teh_wrapper, teh_wrapper, teh_wrapper])
        self.api.add_route('/typeerror', TypeErrornator())
        self.api.add_route('/{user_id}/thingy', TypeErrornator())

        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)
