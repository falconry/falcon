from testtools.matchers import Contains

import falcon
import io
import falcon.testing as testing

import six


class HelloResource:
    sample_status = '200 OK'
    sample_unicode = (u'Hello World! \x80' +
                      six.text_type(testing.rand_string(0, 0)))

    sample_utf8 = sample_unicode.encode('utf-8')

    def __init__(self, mode):
        self.called = False
        self.mode = mode

    def on_get(self, req, resp):
        self.called = True

        self.req, self.resp = req, resp

        resp.status = falcon.HTTP_200

        if 'stream' in self.mode:
            resp.stream = io.BytesIO(self.sample_utf8)

            if 'stream_len' in self.mode:
                resp.stream_len = len(self.sample_utf8)

        if 'body' in self.mode:
            if 'bytes' in self.mode:
                resp.body = self.sample_utf8
            else:
                resp.body = self.sample_unicode

        if 'data' in self.mode:
            resp.data = self.sample_utf8

    def on_head(self, req, resp):
        self.on_get(req, resp)


class NoStatusResource:
    def on_get(self, req, resp):
        pass


class TestHelloWorld(testing.TestBase):

    def before(self):
        self.resource = HelloResource('body')
        self.api.add_route(self.test_route, self.resource)

        self.bytes_resource = HelloResource('body, bytes')
        self.api.add_route('/bytes', self.bytes_resource)

        self.data_resource = HelloResource('data')
        self.api.add_route('/data', self.data_resource)

        self.chunked_resource = HelloResource('stream')
        self.api.add_route('/chunked-stream', self.chunked_resource)

        self.stream_resource = HelloResource('stream, stream_len')
        self.api.add_route('/stream', self.stream_resource)

        self.no_status_resource = NoStatusResource()
        self.api.add_route('/nostatus', self.no_status_resource)

        self.root_resource = testing.TestResource()
        self.api.add_route('/', self.root_resource)

    def after(self):
        pass

    def test_env_headers_list_of_tuples(self):
        env = testing.create_environ(headers=[('User-Agent', 'Falcon-Test')])
        self.assertEqual(env['HTTP_USER_AGENT'], 'Falcon-Test')

    def test_empty_route(self):
        self.simulate_request('')
        self.assertTrue(self.root_resource.called)

    def test_route_negative(self):
        bogus_route = self.test_route + 'x'
        self.simulate_request(bogus_route)

        # Ensure the request was NOT routed to resource
        self.assertFalse(self.resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_body(self):
        body = self.simulate_request(self.test_route)
        resp = self.resource.resp

        content_length = int(self.srmock.headers_dict['content-length'])
        self.assertEqual(content_length, len(self.resource.sample_utf8))

        self.assertEqual(self.srmock.status, self.resource.sample_status)
        self.assertEqual(resp.status, self.resource.sample_status)
        self.assertEqual(resp.body_encoded, self.resource.sample_utf8)
        self.assertEqual(body, [self.resource.sample_utf8])

    def test_body_bytes(self):
        body = self.simulate_request('/bytes')
        resp = self.bytes_resource.resp

        content_length = int(self.srmock.headers_dict['content-length'])
        self.assertEqual(content_length, len(self.resource.sample_utf8))

        self.assertEqual(self.srmock.status, self.resource.sample_status)
        self.assertEqual(resp.status, self.resource.sample_status)
        self.assertEqual(resp.body_encoded, self.resource.sample_utf8)
        self.assertEqual(body, [self.resource.sample_utf8])

    def test_data(self):
        body = self.simulate_request('/data')
        resp = self.data_resource.resp

        content_length = int(self.srmock.headers_dict['content-length'])
        self.assertEqual(content_length, len(self.resource.sample_utf8))

        self.assertEqual(self.srmock.status, self.resource.sample_status)
        self.assertEqual(resp.status, self.resource.sample_status)
        self.assertEqual(resp.data, self.resource.sample_utf8)
        self.assertEqual(body, [self.resource.sample_utf8])

    def test_no_body_on_head(self):
        body = self.simulate_request(self.test_route, method='HEAD')
        self.assertEqual(body, [])
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    def test_stream_chunked(self):
        src = self.simulate_request('/chunked-stream')

        dest = io.BytesIO()
        for chunk in src:
            dest.write(chunk)

        self.assertEqual(dest.getvalue(), self.chunked_resource.sample_utf8)

        for header in self.srmock.headers:
            self.assertNotEqual(header[0].lower(), 'content-length')

    def test_stream_known_len(self):
        src = self.simulate_request('/stream')

        dest = io.BytesIO()
        for chunk in src:
            dest.write(chunk)

        expected_len = self.stream_resource.resp.stream_len
        content_length = ('content-length', str(expected_len))
        self.assertThat(self.srmock.headers, Contains(content_length))
        self.assertEqual(dest.tell(), expected_len)

        self.assertEqual(dest.getvalue(), self.chunked_resource.sample_utf8)

    def test_status_not_set(self):
        body = self.simulate_request('/nostatus')

        self.assertEqual(body, [])
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
