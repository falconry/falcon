from falcon import Request, Response
import falcon.testing as testing


class TestSlots(testing.TestBase):

    def __init__(self):
        self.failed = False
        super(TestSlots, self).__init__()

    def test_slots_request(self):
        env = testing.create_environ()
        req = Request(env)
        try:
            req.doesnt = 'exist'
        except AttributeError:
            self.failed = True
        self.assertFalse(self.failed, 'Unable to add to __slots__ dynamically')

    def test_slots_response(self):
        resp = Response()
        try:
            resp.doesnt = 'exist'
        except AttributeError:
            self.failed = True
        self.assertFalse(self.failed, 'Unable to add to __slots__ dynamically')
