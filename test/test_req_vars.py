import testtools
from testtools.matchers import Equals, MatchesRegex, Contains, Not

from falcon.request import Request
import test.helpers as helpers


class TestReqVars(helpers.TestSuite):

    def prepare(self):
        qs = '?marker=deadbeef&limit=10'
        headers = {
            'Content-Type': 'text/plain',
            'Content-Length': '4829'
        }

        self.req = Request(helpers.create_environ(script='/test',
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
        self.assertThat(actual_url, Equals(expected_url))

    def test_empty_path(self):
        self.req = Request(helpers.create_environ(path=''))
        self.assertThat(self.req.path, Equals('/'))

    def test_content_type(self):
        self.assertThat(self.req.get_header('content-type'),
                        Equals('text/plain'))

    def test_content_length(self):
        self.assertThat(self.req.get_header('content-length'),
                        Equals('4829'))

    def test_http_request_method(self):
        self.assertThat(self.req.method, Equals('GET'))
