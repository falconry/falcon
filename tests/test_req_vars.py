from falcon.request import Request
import falcon.testsuite as testsuite


class TestReqVars(testsuite.TestSuite):

    def prepare(self):
        qs = '?marker=deadbeef&limit=10'
        headers = {
            'Content-Type': 'text/plain',
            'Content-Length': '4829'
        }

        self.req = Request(testsuite.create_environ(script='/test',
                                                    path='/hello',
                                                    query_string=qs,
                                                    headers=headers))

    def test_reconstruct_url(self):
        req = self.req

        scheme = req.protocol
        host = req.get_header('host')
        app = req.app
        path = req.path
        query_string = req.query_string

        expected_url = 'http://falconer/test/hello?marker=deadbeef&limit=10'
        actual_url = ''.join([scheme, '://', host, app, path, query_string])
        self.assertEquals(actual_url, expected_url)

    def test_method(self):
        self.assertEquals(self.req.method, 'GET')

        self.req = Request(testsuite.create_environ(path='', method='HEAD'))
        self.assertEquals(self.req.method, 'HEAD')

    def test_empty_path(self):
        self.req = Request(testsuite.create_environ(path=''))
        self.assertEquals(self.req.path, '/')

    def test_content_type(self):
        self.assertEquals(self.req.get_header('content-type'), 'text/plain')

    def test_content_length(self):
        self.assertEquals(self.req.get_header('content-length'), '4829')
