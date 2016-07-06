import io

import ddt
import six

import falcon
import falcon.testing as testing


# NOTE(kgriffs): Concept from Gunicorn's source (wsgi.py)
class FileWrapper(object):

    def __init__(self, file_like, block_size=8192):
        self.file_like = file_like
        self.block_size = block_size

    def __getitem__(self, key):
        data = self.file_like.read(self.block_size)
        if data:
            return data

        raise IndexError


class HelloResource(object):
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
            if 'filelike' in self.mode:
                stream = io.BytesIO(self.sample_utf8)
            else:
                stream = [self.sample_utf8]

            if 'stream_len' in self.mode:
                stream_len = len(self.sample_utf8)
            else:
                stream_len = None

            if 'use_helper' in self.mode:
                resp.set_stream(stream, stream_len)
            else:
                resp.stream = stream
                resp.stream_len = stream_len

        if 'body' in self.mode:
            if 'bytes' in self.mode:
                resp.body = self.sample_utf8
            else:
                resp.body = self.sample_unicode

        if 'data' in self.mode:
            resp.data = self.sample_utf8

    def on_head(self, req, resp):
        self.on_get(req, resp)


class NoStatusResource(object):
    def on_get(self, req, resp):
        pass


@ddt.ddt
class TestHelloWorld(testing.TestCase):

    def setUp(self):
        super(TestHelloWorld, self).setUp()

    def test_env_headers_list_of_tuples(self):
        env = testing.create_environ(headers=[('User-Agent', 'Falcon-Test')])
        self.assertEqual(env['HTTP_USER_AGENT'], 'Falcon-Test')

    def test_root_route(self):
        doc = {u'message': u'Hello world!'}
        resource = testing.SimpleTestResource(json=doc)
        self.api.add_route('/', resource)

        result = self.simulate_get()
        self.assertEqual(result.json, doc)

    def test_no_route(self):
        result = self.simulate_get('/seenoevil')
        self.assertEqual(result.status_code, 404)

    @ddt.data(
        ('/body', HelloResource('body'), lambda r: r.body.encode('utf-8')),
        ('/bytes', HelloResource('body, bytes'), lambda r: r.body),
        ('/data', HelloResource('data'), lambda r: r.data),
    )
    @ddt.unpack
    def test_body(self, path, resource, get_body):
        self.api.add_route(path, resource)

        result = self.simulate_get(path)
        resp = resource.resp

        content_length = int(result.headers['content-length'])
        self.assertEqual(content_length, len(resource.sample_utf8))

        self.assertEqual(result.status, resource.sample_status)
        self.assertEqual(resp.status, resource.sample_status)
        self.assertEqual(get_body(resp), resource.sample_utf8)
        self.assertEqual(result.content, resource.sample_utf8)

    def test_no_body_on_head(self):
        self.api.add_route('/body', HelloResource('body'))
        result = self.simulate_head('/body')

        self.assertFalse(result.content)
        self.assertEqual(result.status_code, 200)

    def test_stream_chunked(self):
        resource = HelloResource('stream')
        self.api.add_route('/chunked-stream', resource)

        result = self.simulate_get('/chunked-stream')

        self.assertEqual(result.content, resource.sample_utf8)
        self.assertNotIn('content-length', result.headers)

    def test_stream_known_len(self):
        resource = HelloResource('stream, stream_len')
        self.api.add_route('/stream', resource)

        result = self.simulate_get('/stream')
        self.assertTrue(resource.called)

        expected_len = resource.resp.stream_len
        actual_len = int(result.headers['content-length'])
        self.assertEqual(actual_len, expected_len)
        self.assertEqual(len(result.content), expected_len)
        self.assertEqual(result.content, resource.sample_utf8)

    def test_filelike(self):
        resource = HelloResource('stream, stream_len, filelike')
        self.api.add_route('/filelike', resource)

        for file_wrapper in (None, FileWrapper):
            result = self.simulate_get('/filelike', file_wrapper=file_wrapper)
            self.assertTrue(resource.called)

            expected_len = resource.resp.stream_len
            actual_len = int(result.headers['content-length'])
            self.assertEqual(actual_len, expected_len)
            self.assertEqual(len(result.content), expected_len)

    def test_filelike_using_helper(self):
        resource = HelloResource('stream, stream_len, filelike, use_helper')
        self.api.add_route('/filelike-helper', resource)

        result = self.simulate_get('/filelike-helper')
        self.assertTrue(resource.called)

        expected_len = resource.resp.stream_len
        actual_len = int(result.headers['content-length'])
        self.assertEqual(actual_len, expected_len)
        self.assertEqual(len(result.content), expected_len)

    def test_status_not_set(self):
        self.api.add_route('/nostatus', NoStatusResource())

        result = self.simulate_get('/nostatus')

        self.assertFalse(result.content)
        self.assertEqual(result.status_code, 200)
