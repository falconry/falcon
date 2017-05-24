
import falcon


class TestResponseBody(object):

    def test_append_body(self):
        text = 'Hello beautiful world! '
        resp = falcon.Response()
        resp.body = ''

        for token in text.split():
            resp.body += token
            resp.body += ' '

        assert resp.body == text

    def test_response_repr(self):
        resp = falcon.Response()
        _repr = '<%s: %s>' % (resp.__class__.__name__, resp.status)
        assert resp.__repr__() == _repr
