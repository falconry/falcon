import io

import pytest
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


class ClosingBytesIO(io.BytesIO):

    close_called = False

    def close(self):
        super(ClosingBytesIO, self).close()
        self.close_called = True


class NonClosingBytesIO(io.BytesIO):

    # Not callable; test that CloseableStreamIterator ignores it
    close = False


class ClosingFilelikeHelloResource(object):
    sample_status = '200 OK'
    sample_unicode = (u'Hello World! \x80' +
                      six.text_type(testing.rand_string(0, 0)))

    sample_utf8 = sample_unicode.encode('utf-8')

    def __init__(self, stream_factory):
        self.called = False
        self.stream = stream_factory(self.sample_utf8)
        self.stream_len = len(self.sample_utf8)

    def on_get(self, req, resp):
        self.called = True
        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_200
        resp.set_stream(self.stream, self.stream_len)


class NoStatusResource(object):
    def on_get(self, req, resp):
        pass


class TestHelloWorld(object):

    def test_env_headers_list_of_tuples(self):
        env = testing.create_environ(headers=[('User-Agent', 'Falcon-Test')])
        assert env['HTTP_USER_AGENT'] == 'Falcon-Test'

    def test_root_route(self):
        doc = {u'message': u'Hello world!'}
        resource = testing.SimpleTestResource(json=doc)
        app = falcon.APIBuilder() \
            .add_get_route('/', resource.on_get) \
            .build()
        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.json == doc

    def test_no_route(self):
        app = falcon.APIBuilder().build()
        client = testing.TestClient(app)

        result = client.simulate_get('/seenoevil')
        assert result.status_code == 404

    @pytest.mark.parametrize('path,resource,get_body', [
        ('/body', HelloResource('body'), lambda r: r.body.encode('utf-8')),
        ('/bytes', HelloResource('body, bytes'), lambda r: r.body),
        ('/data', HelloResource('data'), lambda r: r.data),
    ])
    def test_body(self, path, resource, get_body):
        app = falcon.APIBuilder() \
            .add_get_route(path, resource.on_get) \
            .add_head_route(path, resource.on_head) \
            .build()
        client = testing.TestClient(app)

        result = client.simulate_get(path)
        resp = resource.resp

        content_length = int(result.headers['content-length'])
        assert content_length == len(resource.sample_utf8)

        assert result.status == resource.sample_status
        assert resp.status == resource.sample_status
        assert get_body(resp) == resource.sample_utf8
        assert result.content == resource.sample_utf8

    def test_no_body_on_head(self):
        resource = HelloResource('body')
        app = falcon.APIBuilder() \
            .add_head_route('/body', resource.on_head) \
            .build()
        client = testing.TestClient(app)

        result = client.simulate_head('/body')

        assert not result.content
        assert result.status_code == 200

    def test_stream_chunked(self):
        resource = HelloResource('stream')
        app = falcon.APIBuilder() \
            .add_get_route('/chunked-stream', resource.on_get) \
            .build()
        client = testing.TestClient(app)

        result = client.simulate_get('/chunked-stream')

        assert result.content == resource.sample_utf8
        assert 'content-length' not in result.headers

    def test_stream_known_len(self):
        resource = HelloResource('stream, stream_len')
        app = falcon.APIBuilder() \
            .add_get_route('/stream', resource.on_get) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_get('/stream')
        assert resource.called

        expected_len = resource.resp.stream_len
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len
        assert result.content == resource.sample_utf8

    def test_filelike(self):
        resource = HelloResource('stream, stream_len, filelike')
        app = falcon.APIBuilder() \
            .add_get_route('/filelike', resource.on_get) \
            .build()
        client = testing.TestClient(app)

        for file_wrapper in (None, FileWrapper):
            result = client.simulate_get('/filelike', file_wrapper=file_wrapper)
            assert resource.called

            expected_len = resource.resp.stream_len
            actual_len = int(result.headers['content-length'])
            assert actual_len == expected_len
            assert len(result.content) == expected_len

        for file_wrapper in (None, FileWrapper):
            result = client.simulate_get('/filelike', file_wrapper=file_wrapper)
            assert resource.called

            expected_len = resource.resp.stream_len
            actual_len = int(result.headers['content-length'])
            assert actual_len == expected_len
            assert len(result.content) == expected_len

    @pytest.mark.parametrize('stream_factory,assert_closed', [
        (ClosingBytesIO, True),  # Implements close()
        (NonClosingBytesIO, False),  # Has a non-callable "close" attr
    ])
    def test_filelike_closing(self, stream_factory, assert_closed):
        resource = ClosingFilelikeHelloResource(stream_factory)
        app = falcon.APIBuilder() \
            .add_get_route('/filelike-closing', resource.on_get) \
            .build()
        client = testing.TestClient(app)

        result = client.simulate_get('/filelike-closing', file_wrapper=None)
        assert resource.called

        expected_len = resource.resp.stream_len
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

        if assert_closed:
            assert resource.stream.close_called

    def test_filelike_using_helper(self):
        resource = HelloResource('stream, stream_len, filelike, use_helper')
        app = falcon.APIBuilder() \
            .add_get_route('/filelike-helper', resource.on_get) \
            .build()

        client = testing.TestClient(app)

        result = client.simulate_get('/filelike-helper')
        assert resource.called

        expected_len = resource.resp.stream_len
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

    def test_status_not_set(self):
        resource = NoStatusResource()
        app = falcon.APIBuilder() \
            .add_get_route('/nostatus', resource.on_get) \
            .build()
        client = testing.TestClient(app)

        result = client.simulate_get('/nostatus')

        assert not result.content
        assert result.status_code == 200
