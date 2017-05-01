
import falcon
import falcon.testing as testing


class TestResponseBody(testing.TestBase):

    def test_append_body(self):
        text = 'Hello beautiful world! '
        resp = falcon.Response()
        resp.body = ''

        for token in text.split():
            resp.body += token
            resp.body += ' '

        self.assertEqual(resp.body, text)

    def test_response_repr(self):
        resp = falcon.Response()
        _repr = '<%s: %s>' % (resp.__class__.__name__, resp.status)
        self.assertEqual(resp.__repr__(), _repr)
