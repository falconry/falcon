
import falcon
import falcon.testing as testing


class TestResponseBody(testing.TestBase):

    def test_append_body(self):
        text = "Hello beautiful world! "
        resp = falcon.Response()
        resp.body = ""

        for token in text.split():
            resp.body += token
            resp.body += " "

        self.assertEqual(resp.body, text)

    def test_redirect(self):
        resp = falcon.Response()
        resp.redirect('http://localhost/anything')
        self.assertEqual(resp.status, "303 See Other")
        self.assertEqual(resp._headers['Location'], 'http://localhost/anything')

    def test_redirect_permanent(self):
        resp = falcon.Response()
        resp.redirect('http://localhost/anything', permanent=True)
        self.assertEqual(resp.status, "301 Moved Permanently")
        self.assertEqual(resp._headers['Location'], 'http://localhost/anything')

