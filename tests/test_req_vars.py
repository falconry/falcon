from falcon.request import Request
import falcon.testing as testing


class TestReqVars(testing.TestBase):

    def before(self):
        qs = '?marker=deadbeef&limit=10'

        headers = {
            'Content-Type': 'text/plain',
            'Content-Length': '4829',
        }

        self.url = 'http://falconer/test/hello?marker=deadbeef&limit=10'
        self.req = Request(testing.create_environ(app='/test',
                                                  path='/hello',
                                                  query_string=qs,
                                                  headers=headers))

    def test_missing_qs(self):
        env = testing.create_environ()
        if 'QUERY_STRING' in env:
            del env['QUERY_STRING']

        # Should not cause an exception when Request is instantiated
        Request(env)

    def test_reconstruct_url(self):
        req = self.req

        scheme = req.protocol
        host = req.get_header('host')
        app = req.app
        path = req.path
        query_string = req.query_string

        actual_url = ''.join([scheme, '://', host, app, path, query_string])
        self.assertEquals(self.url, actual_url)

    def test_url(self):
        self.assertEquals(self.url, self.req.url)

    def test_range(self):
        headers = {'Range': '10-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEquals((10, -1), req.range)

        headers = {'Range': '10-20'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEquals((10, 20), req.range)

        headers = {'Range': '-10240'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEquals((-10240, -1), req.range)

        headers = {'Range': '10240'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': ''}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': '-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': '--'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': '-3-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': '-3-4'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': '3-3-4'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': '3-3-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

        headers = {'Range': None}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, req.range)

    def test_missing_attribute_header(self):
        req = Request(testing.create_environ())
        self.assertEquals(None, req.range)

        req = Request(testing.create_environ())
        self.assertEquals(None, req.content_length)

    def test_content_length(self):
        headers = {'content-length': '5656'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEquals(5656, req.content_length)

    def test_bogus_content_length(self):
        headers = {'content-length': 'fuzzy-bunnies'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEquals(None, req.content_length)

    def test_attribute_headers(self):
        date = testing.httpnow()
        hash = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        auth = 'HMAC_SHA1 c590afa9bb59191ffab30f223791e82d3fd3e3af'
        agent = 'curl/7.24.0 (x86_64-apple-darwin12.0)'

        self._test_attribute_header('Accept', 'x-falcon', 'accept')

        self._test_attribute_header('Authorization', auth, 'auth')

        self._test_attribute_header('Content-Type', 'text/plain',
                                    'content_type')
        self._test_attribute_header('Expect', '100-continue', 'expect')
        self._test_attribute_header('Date', date, 'date')

        self._test_attribute_header('If-Match', hash, 'if_match')
        self._test_attribute_header('If-Modified-Since', date,
                                    'if_modified_since')
        self._test_attribute_header('If-None-Match', hash, 'if_none_match')
        self._test_attribute_header('If-Range', hash, 'if_range')
        self._test_attribute_header('If-Unmodified-Since', date,
                                    'if_unmodified_since')

        self._test_attribute_header('User-Agent', agent, 'user_agent')

    def test_method(self):
        self.assertEquals(self.req.method, 'GET')

        self.req = Request(testing.create_environ(path='', method='HEAD'))
        self.assertEquals(self.req.method, 'HEAD')

    def test_empty_path(self):
        self.req = Request(testing.create_environ(path=''))
        self.assertEquals(self.req.path, '/')

    def test_content_type_method(self):
        self.assertEquals(self.req.get_header('content-type'), 'text/plain')

    def test_content_length_method(self):
        self.assertEquals(self.req.get_header('content-length'), '4829')

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _test_attribute_header(self, name, value, attr):
        headers = {name: value}
        req = Request(testing.create_environ(headers=headers))
        self.assertEquals(value, getattr(req, attr))

        headers = {name: None}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(None, getattr(req, attr))
