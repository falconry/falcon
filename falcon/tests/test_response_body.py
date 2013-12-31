
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
