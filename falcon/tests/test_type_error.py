import falcon
import falcon.testing as testing


class Thinger(object):
    def __init__(self, number):
        pass


def teh_wrapper(req, resp, params):
    pass


class TypeErrornatorResource(object):

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

    @falcon.after(teh_wrapper)
    @falcon.after(teh_wrapper)
    def on_post(self, req, resp, user_id):
        # Responder has incorrect args
        Thinger()

    @falcon.before(teh_wrapper)
    @falcon.before(teh_wrapper)
    def on_delete(self, req, resp, user_id):
        # Responder has incorrect args
        Thinger()


@falcon.before(teh_wrapper)
@falcon.before(teh_wrapper)
class ClassBeforeWrapperResouce(object):

    def on_get(self, req, resp, user_id):
        silly = True

        # Call an uncallable
        return silly()


@falcon.after(teh_wrapper)
@falcon.after(teh_wrapper)
class ClassAfterWrapperResouce(object):

    def on_get(self, req, resp, user_id):
        silly = True

        # Call an uncallable
        return silly()


@falcon.before(teh_wrapper)
@falcon.after(teh_wrapper)
class ClassMixedWrapperResouce(object):

    def on_get(self, req, resp, user_id):
        silly = True

        # Call an uncallable
        return silly()


class TestTypeError(testing.TestBase):

    def before(self):
        self.api = falcon.API(before=teh_wrapper)
        self.api.add_route('/typeerror', TypeErrornatorResource())
        self.api.add_route('/{user_id}/thingy', TypeErrornatorResource())

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

    def test_wrapped_after_not_enough_init_args(self):
        self.api = falcon.API(after=[teh_wrapper, teh_wrapper])
        self.api.add_route('/{user_id}/thingy', TypeErrornatorResource())

        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_double_wrapped_not_enough_init_args(self):
        self.api = falcon.API(before=[teh_wrapper, teh_wrapper])
        self.api.add_route('/{user_id}/thingy', TypeErrornatorResource())

        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_triple_wrapped_not_enough_init_args(self):
        self.api = falcon.API(before=[teh_wrapper, teh_wrapper, teh_wrapper])
        self.api.add_route('/{user_id}/thingy', TypeErrornatorResource())

        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_local_wrapped_not_enough_init_args(self):
        self.api = falcon.API()
        self.api.add_route('/{user_id}/thingy', TypeErrornatorResource())

        self.simulate_request('/123/thingy', method='POST')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

        self.simulate_request('/123/thingy', method='DELETE')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_class_before_wrapper_type_not_callable(self):
        self.api = falcon.API()
        self.api.add_route('/{user_id}/thingy', ClassBeforeWrapperResouce())

        self.simulate_request('/123/thingy')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_class_after_wrapper_type_not_callable(self):
        self.api = falcon.API()
        self.api.add_route('/{user_id}/thingy', ClassAfterWrapperResouce())

        self.simulate_request('/123/thingy')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)

    def test_class_mixed_wrapper_type_not_callable(self):
        self.api = falcon.API()
        self.api.add_route('/{user_id}/thingy', ClassMixedWrapperResouce())

        self.simulate_request('/123/thingy')
        self.assertEquals(self.srmock.status, falcon.HTTP_500)
