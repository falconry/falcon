from falcon import Request, Response
import falcon.testing as testing


class TestSlots(testing.TestBase):

    def test_slots_request(self):
        env = testing.create_environ()
        req = Request(env)

        try:
            req.doesnt = 'exist'
        except AttributeError:
            self.fail('Unable to add additional variables dynamically')

    def test_slots_response(self):
        resp = Response()

        try:
            resp.doesnt = 'exist'
        except AttributeError:
            self.fail('Unable to add additional variables dynamically')
