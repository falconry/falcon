import falcon.testsuite as testsuite


class TestRequestBody(testsuite.TestSuite):

    def prepare(self):
        self.resource = testsuite.TestResource()
        self.api.add_route('/', self.resource)

    def test_empty_body(self):
        self._simulate_request('/', body='')
        stream = self.resource.req.stream

        stream.seek(0, 2)
        self.assertEquals(stream.tell(), 0)

    def test_tiny_body(self):
        expected_body = '.'
        self._simulate_request('', body=expected_body)
        stream = self.resource.req.stream

        actual_body = stream.read(1)
        self.assertEquals(actual_body, expected_body.encode('utf-8'))

        stream.seek(0, 2)
        self.assertEquals(stream.tell(), 1)

    def test_read_body(self):
        expected_body = testsuite.rand_string(2, 1 * 1024 * 1024)
        expected_len = len(expected_body)
        headers = {'Content-Length': str(expected_len)}

        self._simulate_request('', body=expected_body, headers=headers)

        content_len = self.resource.req.get_header('content-length')
        self.assertEqual(content_len, str(expected_len))

        stream = self.resource.req.stream

        actual_body = stream.read()
        self.assertEquals(actual_body, expected_body.encode('utf-8'))

        stream.seek(0, 2)
        self.assertEquals(stream.tell(), expected_len)

        self.assertEquals(stream.tell(), expected_len)
