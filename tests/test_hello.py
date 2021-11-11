import io

import pytest

import falcon
from falcon import testing


@pytest.fixture
def client():
    return testing.TestClient(falcon.App())


# NOTE(kgriffs): Concept from Gunicorn's source (wsgi.py)
class FileWrapper:
    def __init__(self, file_like, block_size=8192):
        self.file_like = file_like
        self.block_size = block_size

    def __getitem__(self, key):
        data = self.file_like.read(self.block_size)
        if data:
            return data

        raise IndexError


class HelloResource:
    sample_status = '200 OK'
    sample_unicode = 'Hello World! \x80' + testing.rand_string(0, 0)
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
                resp.content_length = stream_len

        if 'body' in self.mode:
            if 'bytes' in self.mode:
                resp.text = self.sample_utf8
            else:
                resp.text = self.sample_unicode

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
    close = False  # type: ignore


class ClosingFilelikeHelloResource:
    sample_status = '200 OK'
    sample_unicode = 'Hello World! \x80' + testing.rand_string(0, 0)

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


class NoStatusResource:
    def on_get(self, req, resp):
        pass


class TestHelloWorld:
    def test_env_headers_list_of_tuples(self):
        env = testing.create_environ(headers=[('User-Agent', 'Falcon-Test')])
        assert env['HTTP_USER_AGENT'] == 'Falcon-Test'

    def test_root_route(self, client):
        doc = {'message': 'Hello world!'}
        resource = testing.SimpleTestResource(json=doc)
        client.app.add_route('/', resource)

        result = client.simulate_get()
        assert result.json == doc

    def test_no_route(self, client):
        result = client.simulate_get('/seenoevil')
        assert result.status_code == 404

    @pytest.mark.parametrize(
        'path,resource,get_body',
        [
            ('/body', HelloResource('body'), lambda r: r.text.encode('utf-8')),
            ('/bytes', HelloResource('body, bytes'), lambda r: r.text),
            ('/data', HelloResource('data'), lambda r: r.data),
        ],
    )
    def test_body(self, client, path, resource, get_body):
        client.app.add_route(path, resource)

        result = client.simulate_get(path)
        resp = resource.resp

        content_length = int(result.headers['content-length'])
        assert content_length == len(resource.sample_utf8)

        assert result.status == resource.sample_status
        assert resp.status == resource.sample_status
        assert get_body(resp) == resource.sample_utf8
        assert result.content == resource.sample_utf8

    def test_no_body_on_head(self, client):
        resource = HelloResource('body')
        client.app.add_route('/body', resource)
        result = client.simulate_head('/body')

        assert not result.content
        assert result.status_code == 200
        assert resource.called
        assert result.headers['content-length'] == str(len(HelloResource.sample_utf8))

    def test_stream_chunked(self, client):
        resource = HelloResource('stream')
        client.app.add_route('/chunked-stream', resource)

        result = client.simulate_get('/chunked-stream')

        assert result.content == resource.sample_utf8
        assert 'content-length' not in result.headers

    def test_stream_known_len(self, client):
        resource = HelloResource('stream, stream_len')
        client.app.add_route('/stream', resource)

        result = client.simulate_get('/stream')
        assert resource.called

        expected_len = int(resource.resp.content_length)
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len
        assert result.content == resource.sample_utf8

    def test_filelike(self, client):
        resource = HelloResource('stream, stream_len, filelike')
        client.app.add_route('/filelike', resource)

        for file_wrapper in (None, FileWrapper):
            result = client.simulate_get('/filelike', file_wrapper=file_wrapper)
            assert resource.called

            expected_len = int(resource.resp.content_length)
            actual_len = int(result.headers['content-length'])
            assert actual_len == expected_len
            assert len(result.content) == expected_len

        for file_wrapper in (None, FileWrapper):
            result = client.simulate_get('/filelike', file_wrapper=file_wrapper)
            assert resource.called

            expected_len = int(resource.resp.content_length)
            actual_len = int(result.headers['content-length'])
            assert actual_len == expected_len
            assert len(result.content) == expected_len

    @pytest.mark.parametrize(
        'stream_factory,assert_closed',
        [
            (ClosingBytesIO, True),  # Implements close()
            (NonClosingBytesIO, False),  # Has a non-callable "close" attr
        ],
    )
    def test_filelike_closing(self, client, stream_factory, assert_closed):
        resource = ClosingFilelikeHelloResource(stream_factory)
        client.app.add_route('/filelike-closing', resource)

        result = client.simulate_get('/filelike-closing', file_wrapper=None)
        assert resource.called

        expected_len = int(resource.resp.content_length)
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

        if assert_closed:
            assert resource.stream.close_called

    def test_filelike_using_helper(self, client):
        resource = HelloResource('stream, stream_len, filelike, use_helper')
        client.app.add_route('/filelike-helper', resource)

        result = client.simulate_get('/filelike-helper')
        assert resource.called

        expected_len = int(resource.resp.content_length)
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

    def test_status_not_set(self, client):
        client.app.add_route('/nostatus', NoStatusResource())

        result = client.simulate_get('/nostatus')

        assert not result.content
        assert result.status_code == 200
