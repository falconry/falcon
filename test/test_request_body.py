import testtools

import helpers


class TestRequestBody(helpers.TestSuite):

    def prepare(self):
        self.reqhandler = helpers.RequestHandler()
        self.api.add_route('/', self.reqhandler)

    def test_empty_body(self):
        self._simulate_request('/', body='')
        stream = self.reqhandler.req.body

        stream.seek(0, 2)
        self.assertEquals(stream.tell(), 0)

    def test_tiny_body(self):
        expected_body = '.'
        self._simulate_request('', body=expected_body)
        stream = self.reqhandler.req.body

        actual_body = stream.read(1)
        self.assertEquals(actual_body, expected_body)

        stream.seek(0, 2)
        self.assertEquals(stream.tell(), 1)

    def test_read_body(self):
        expected_body = helpers.rand_string(2, 1 * 1024 * 1024)
        expected_len = len(expected_body)
        headers = {'Content-Length': str(expected_len)}

        self._simulate_request('', body=expected_body, headers=headers)

        content_len = self.reqhandler.req.get_header('content-length')
        self.assertEqual(content_len, str(expected_len))

        stream = self.reqhandler.req.body

        actual_body = stream.read()
        self.assertEquals(actual_body, expected_body)

        stream.seek(0, 2)
        self.assertEquals(stream.tell(), expected_len)

        self.assertEquals(stream.tell(), expected_len)
