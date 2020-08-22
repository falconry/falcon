import io
import os
import tempfile

import aiofiles
import pytest

import falcon
from falcon import testing
import falcon.asgi

from _util import disable_asgi_non_coroutine_wrapping  # NOQA


SIZE_1_KB = 1024


@pytest.fixture
def client():
    return testing.TestClient(falcon.asgi.App())


class DataReaderWithoutClose:
    def __init__(self, data):
        self._stream = io.BytesIO(data)
        self.close_called = False

    async def read(self, num_bytes):
        return self._stream.read(num_bytes)


class DataReader(DataReaderWithoutClose):
    async def close(self):
        self.close_called = True


class HelloResource:
    sample_status = '200 OK'
    sample_unicode = ('Hello World! \x80 - ' + testing.rand_string(0, 5))
    sample_utf8 = sample_unicode.encode('utf-8')

    def __init__(self, mode):
        self.called = False
        self.mode = mode

    async def on_get(self, req, resp):
        self.called = True
        self.req, self.resp = req, resp

        resp.status = falcon.HTTP_200

        if 'stream' in self.mode:
            if 'filelike' in self.mode:
                stream = DataReader(self.sample_utf8)
            else:
                async def data_emitter():
                    for b in self.sample_utf8:
                        yield bytes([b])

                if 'stream_genfunc' in self.mode:
                    stream = data_emitter
                elif 'stream_nongenfunc' in self.mode:
                    stream = 42
                else:
                    stream = data_emitter()

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

    async def on_head(self, req, resp):
        await self.on_get(req, resp)


class ClosingFilelikeHelloResource:
    sample_status = '200 OK'
    sample_unicode = ('Hello World! \x80' + testing.rand_string(0, 0))

    sample_utf8 = sample_unicode.encode('utf-8')

    def __init__(self, stream_factory):
        self.called = False
        self.stream = stream_factory(self.sample_utf8)
        self.stream_len = len(self.sample_utf8)

    async def on_get(self, req, resp):
        self.called = True
        self.req, self.resp = req, resp
        resp.status = falcon.HTTP_200
        resp.set_stream(self.stream, self.stream_len)


class AIOFilesHelloResource:
    def __init__(self):
        self.sample_utf8 = testing.rand_string(8 * SIZE_1_KB, 16 * SIZE_1_KB).encode()

        fh, self.tempfile_name = tempfile.mkstemp()
        with open(fh, 'wb') as f:
            f.write(self.sample_utf8)

        self._aiofiles = None

    @property
    def aiofiles_closed(self):
        return not self._aiofiles or self._aiofiles.closed

    def cleanup(self):
        os.remove(self.tempfile_name)

    async def on_get(self, req, resp):
        self._aiofiles = await aiofiles.open(self.tempfile_name, 'rb')
        resp.stream = self._aiofiles


class NoStatusResource:
    async def on_get(self, req, resp):
        pass


class PartialCoroutineResource:
    def on_get(self, req, resp):
        pass

    async def on_post(self, req, resp):
        pass


class TestHelloWorld:

    def test_env_headers_list_of_tuples(self):
        env = testing.create_environ(headers=[('User-Agent', 'Falcon-Test')])
        assert env['HTTP_USER_AGENT'] == 'Falcon-Test'

    def test_root_route(self, client):
        doc = {'message': 'Hello world!'}
        resource = testing.SimpleTestResourceAsync(json=doc)
        client.app.add_route('/', resource)

        result = client.simulate_get()
        assert result.json == doc

    def test_no_route(self, client):
        result = client.simulate_get('/seenoevil')
        assert result.status_code == 404

    @pytest.mark.parametrize('path,resource,get_body', [
        ('/body', HelloResource('body'), lambda r: r.text.encode('utf-8')),
        ('/bytes', HelloResource('body, bytes'), lambda r: r.text),
        ('/data', HelloResource('data'), lambda r: r.data),
    ])
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

        result = client.simulate_get('/filelike')
        assert resource.called

        expected_len = int(resource.resp.content_length)
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

        result = client.simulate_get('/filelike')
        assert resource.called

        expected_len = int(resource.resp.content_length)
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

    def test_genfunc_error(self, client):
        resource = HelloResource('stream, stream_len, stream_genfunc')
        client.app.add_route('/filelike', resource)

        with pytest.raises(TypeError):
            client.simulate_get('/filelike')

    def test_nongenfunc_error(self, client):
        resource = HelloResource('stream, stream_len, stream_nongenfunc')
        client.app.add_route('/filelike', resource)

        with pytest.raises(TypeError):
            client.simulate_get('/filelike')

    @pytest.mark.parametrize('stream_factory,assert_closed', [
        (DataReader, True),  # Implements close()
        (DataReaderWithoutClose, False),
    ])
    def test_filelike_closing(self, client, stream_factory, assert_closed):
        resource = ClosingFilelikeHelloResource(stream_factory)
        client.app.add_route('/filelike-closing', resource)

        result = client.simulate_get('/filelike-closing')
        assert resource.called

        expected_len = int(resource.resp.content_length)
        actual_len = int(result.headers['content-length'])
        assert actual_len == expected_len
        assert len(result.content) == expected_len

        if assert_closed:
            assert resource.stream.close_called

    def test_filelike_closing_aiofiles(self, client):
        resource = AIOFilesHelloResource()
        try:
            client.app.add_route('/filelike-closing', resource)

            result = client.simulate_get('/filelike-closing')

            assert result.status_code == 200
            assert 'content-length' not in result.headers
            assert result.content == resource.sample_utf8

            assert resource.aiofiles_closed

        finally:
            resource.cleanup()

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

    def test_coroutine_required(self, client):
        with disable_asgi_non_coroutine_wrapping():
            with pytest.raises(TypeError) as exinfo:
                client.app.add_route('/', PartialCoroutineResource())

            assert 'responder must be a non-blocking async coroutine' in str(exinfo.value)

    def test_noncoroutine_required(self):
        wsgi_app = falcon.App()

        with pytest.raises(TypeError) as exinfo:
            wsgi_app.add_route('/', PartialCoroutineResource())

        assert 'responder must be a regular synchronous method' in str(exinfo.value)
