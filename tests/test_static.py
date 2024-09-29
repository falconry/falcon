import errno
import io
import os
import pathlib
import posixpath

import pytest

import falcon
from falcon.routing import StaticRoute
from falcon.routing import StaticRouteAsync
from falcon.routing.static import _BoundedFile
import falcon.testing as testing


def normalize_path(path):
    # NOTE(vytas): On CPython 3.13, ntpath.isabs() no longer returns True for
    #   Unix-like absolute paths that start with a single \.
    #   We work around this in tests by prepending a fake drive D:\ on Windows.
    #   See also: https://github.com/python/cpython/issues/117352
    is_pathlib_path = isinstance(path, pathlib.Path)
    if not is_pathlib_path and not posixpath.isabs(path):
        return path

    path = os.path.normpath(path)
    if path.startswith('\\'):
        path = 'D:' + path
    return pathlib.Path(path) if is_pathlib_path else path


@pytest.fixture()
def client(asgi, util, monkeypatch):
    def add_static_route_normalized(obj, prefix, directory, **kwargs):
        add_static_route_orig(obj, prefix, normalize_path(directory), **kwargs)

    app = util.create_app(asgi=asgi)

    app_cls = type(app)
    add_static_route_orig = app_cls.add_static_route
    monkeypatch.setattr(app_cls, 'add_static_route', add_static_route_normalized)

    client = testing.TestClient(app)
    client.asgi = asgi
    return client


def create_sr(asgi, prefix, directory, **kwargs):
    sr_type = StaticRouteAsync if asgi else StaticRoute
    return sr_type(prefix, normalize_path(directory), **kwargs)


@pytest.fixture
def patch_open(monkeypatch):
    def patch(content=None, validate=None):
        def open(path, mode):
            class FakeFD(int):
                pass

            class FakeStat:
                def __init__(self, size):
                    self.st_size = size

            if validate:
                validate(path)

            data = path.encode() if content is None else content
            fake_file = io.BytesIO(data)
            fd = FakeFD(1337)
            fd._stat = FakeStat(len(data))
            fake_file.fileno = lambda: fd

            patch.current_file = fake_file
            return fake_file

        monkeypatch.setattr(io, 'open', open)
        monkeypatch.setattr(os, 'fstat', lambda fileno: fileno._stat)

    patch.current_file = None
    return patch


@pytest.mark.parametrize(
    'uri',
    [
        # Root
        '/static',
        '/static/',
        '/static/.',
        # Attempt to jump out of the directory
        '/static/..',
        '/static/../.',
        '/static/.././etc/passwd',
        '/static/../etc/passwd',
        '/static/css/../../secret',
        '/static/css/../../etc/passwd',
        '/static/./../etc/passwd',
        # The file system probably won't process escapes, but better safe than sorry
        '/static/css/../.\\056/etc/passwd',
        '/static/./\\056./etc/passwd',
        '/static/\\056\\056/etc/passwd',
        # Double slash
        '/static//test.css',
        '/static//COM10',
        '/static/path//test.css',
        '/static/path///test.css',
        '/static/path////test.css',
        '/static/path/foo//test.css',
        # Control characters (0x00–0x1f and 0x80–0x9f)
        '/static/.\x00ssh/authorized_keys',
        '/static/.\x1fssh/authorized_keys',
        '/static/.\x80ssh/authorized_keys',
        '/static/.\x9fssh/authorized_keys',
        # Reserved characters (~, ?, <, >, :, *, |, ', and ")
        '/static/~/.ssh/authorized_keys',
        '/static/.ssh/authorized_key?',
        '/static/.ssh/authorized_key>foo',
        '/static/.ssh/authorized_key|foo',
        '/static/.ssh/authorized_key<foo',
        '/static/something:something',
        '/static/thing*.sql',
        "/static/'thing'.sql",
        '/static/"thing".sql',
        # Trailing periods and spaces
        '/static/something.',
        '/static/something..',
        '/static/something ',
        '/static/ something ',
        '/static/ something ',
        '/static/something\t',
        '/static/\tsomething',
        # Too long
        '/static/' + ('t' * StaticRoute._MAX_NON_PREFIXED_LEN) + 'x',
        # Invalid unicode character
        '/static/\ufffdsomething',
    ],
)
def test_bad_path(asgi, util, uri, patch_open):
    patch_open(b'')

    sr = create_sr(asgi, '/static', '/var/www/statics')

    req = util.create_req(asgi, host='test.com', path=uri, root_path='statics')

    resp = util.create_resp(asgi)

    with pytest.raises(falcon.HTTPNotFound):
        if asgi:
            falcon.async_to_sync(sr, req, resp)
        else:
            sr(req, resp)


@pytest.mark.parametrize(
    'prefix, directory',
    [
        ('static', '/var/www/statics'),
        ('/static', './var/www/statics'),
        ('/static', 'statics'),
        ('/static', '../statics'),
    ],
)
def test_invalid_args(client, prefix, directory):
    with pytest.raises(ValueError):
        create_sr(client.asgi, prefix, directory)

    with pytest.raises(ValueError):
        client.app.add_static_route(prefix, directory)


@pytest.mark.parametrize(
    'default',
    [
        'not-existing-file',
        # directories
        '.',
        '/tmp',
    ],
)
def test_invalid_args_fallback_filename(client, default):
    prefix, directory = '/static', '/var/www/statics'
    with pytest.raises(ValueError, match='fallback_filename'):
        create_sr(client.asgi, prefix, directory, fallback_filename=default)

    with pytest.raises(ValueError, match='fallback_filename'):
        client.app.add_static_route(prefix, directory, fallback_filename=default)


# NOTE(caselit) depending on the system configuration mime types
# can have alternative names
_MIME_ALTERNATIVE = {
    'application/zip': ('application/zip', 'application/x-zip-compressed')
}


@pytest.mark.parametrize(
    'uri_prefix, uri_path, expected_path, mtype',
    [
        ('/static/', '/css/test.css', '/css/test.css', 'text/css'),
        ('/static', '/css/test.css', '/css/test.css', 'text/css'),
        (
            '/static',
            '/' + ('t' * StaticRoute._MAX_NON_PREFIXED_LEN),
            '/' + ('t' * StaticRoute._MAX_NON_PREFIXED_LEN),
            'application/octet-stream',
        ),
        ('/static', '/.test.css', '/.test.css', 'text/css'),
        ('/some/download/', '/report.pdf', '/report.pdf', 'application/pdf'),
        (
            '/some/download/',
            '/Fancy Report.pdf',
            '/Fancy Report.pdf',
            'application/pdf',
        ),
        ('/some/download', '/report.zip', '/report.zip', 'application/zip'),
        ('/some/download', '/foo/../report.zip', '/report.zip', 'application/zip'),
        (
            '/some/download',
            '/foo/../bar/../report.zip',
            '/report.zip',
            'application/zip',
        ),
        (
            '/some/download',
            '/foo/bar/../../report.zip',
            '/report.zip',
            'application/zip',
        ),
    ],
)
def test_good_path(asgi, util, uri_prefix, uri_path, expected_path, mtype, patch_open):
    patch_open()

    sr = create_sr(asgi, uri_prefix, '/var/www/statics')

    req_path = uri_prefix[:-1] if uri_prefix.endswith('/') else uri_prefix
    req_path += uri_path

    req = util.create_req(asgi, host='test.com', path=req_path, root_path='statics')

    resp = util.create_resp(asgi)

    if asgi:

        async def run():
            await sr(req, resp)
            return await resp.stream.read()

        body = falcon.async_to_sync(run)
    else:
        sr(req, resp)
        body = resp.stream.read()

    assert resp.content_type in _MIME_ALTERNATIVE.get(mtype, (mtype,))
    assert body.decode() == normalize_path('/var/www/statics' + expected_path)
    assert resp.headers.get('accept-ranges') == 'bytes'


@pytest.mark.parametrize(
    'range_header, exp_content_range, exp_content',
    [
        ('bytes=1-3', 'bytes 1-3/16', '123'),
        ('bytes=-3', 'bytes 13-15/16', 'def'),
        ('bytes=8-', 'bytes 8-15/16', '89abcdef'),
        ('words=1-3', None, '0123456789abcdef'),  # unknown unit; ignore
        ('bytes=15-30', 'bytes 15-15/16', 'f'),
        ('bytes=0-30', 'bytes 0-15/16', '0123456789abcdef'),
        ('bytes=-30', 'bytes 0-15/16', '0123456789abcdef'),
    ],
)
@pytest.mark.parametrize('use_fallback', [True, False])
def test_range_requests(
    client,
    range_header,
    exp_content_range,
    exp_content,
    patch_open,
    monkeypatch,
    use_fallback,
):
    def validate(path):
        if use_fallback and not path.endswith('index.html'):
            raise OSError(errno.ENOENT, 'File not found')

    patch_open(b'0123456789abcdef', validate=validate)

    monkeypatch.setattr('os.path.isfile', lambda file: file.endswith('index.html'))

    client.app.add_static_route(
        '/downloads', '/opt/somesite/downloads', fallback_filename='index.html'
    )

    response = client.simulate_request(
        path='/downloads/thing.zip', headers={'Range': range_header}
    )
    if exp_content_range is None:
        assert response.status == falcon.HTTP_200
    else:
        assert response.status == falcon.HTTP_206
    assert response.text == exp_content
    assert int(response.headers['Content-Length']) == len(exp_content)
    assert response.headers.get('Content-Range') == exp_content_range
    assert response.headers.get('Accept-Ranges') == 'bytes'
    if use_fallback:
        assert response.headers.get('Content-Type') == 'text/html'
    else:
        assert (
            response.headers.get('Content-Type') in _MIME_ALTERNATIVE['application/zip']
        )


@pytest.mark.parametrize(
    'range_header',
    [
        'bytes=1-3',
        'bytes=-3',
        'bytes=8-',
        'words=1-3',
        'bytes=15-30',
        'bytes=0-30',
        'bytes=-30',
    ],
)
def test_range_request_zero_length(client, range_header, patch_open):
    patch_open(b'')

    client.app.add_static_route('/downloads', '/opt/somesite/downloads')

    response = client.simulate_request(
        path='/downloads/thing.zip', headers={'Range': range_header}
    )
    assert response.status == falcon.HTTP_200
    assert response.text == ''
    assert 'Content-Range' not in response.headers
    assert response.headers.get('Accept-Ranges') == 'bytes'


@pytest.mark.parametrize(
    'range_header, exp_status',
    [
        ('1-3', falcon.HTTP_400),
        ('bytes=0-0,-1', falcon.HTTP_400),
        ('bytes=8-4', falcon.HTTP_400),
        ('bytes=1--3', falcon.HTTP_400),
        ('bytes=--0', falcon.HTTP_400),
        ('bytes=100-200', falcon.HTTP_416),
        ('bytes=100-', falcon.HTTP_416),
        ('bytes=16-20', falcon.HTTP_416),
        ('bytes=16-', falcon.HTTP_416),
    ],
)
def test_bad_range_requests(client, range_header, exp_status, patch_open):
    patch_open(b'0123456789abcdef')

    client.app.add_static_route('/downloads', '/opt/somesite/downloads')

    response = client.simulate_request(
        path='/downloads/thing.zip', headers={'Range': range_header}
    )
    assert response.status == exp_status
    if response.status == falcon.HTTP_416:
        assert response.headers.get('Content-Range') == 'bytes */16'


def test_pathlib_path(asgi, util, patch_open):
    patch_open()

    sr = create_sr(asgi, '/static/', pathlib.Path('/var/www/statics'))
    req_path = '/static/css/test.css'

    req = util.create_req(asgi, host='test.com', path=req_path, root_path='statics')

    resp = util.create_resp(asgi)

    if asgi:

        async def run():
            await sr(req, resp)
            return await resp.stream.read()

        body = falcon.async_to_sync(run)
    else:
        sr(req, resp)
        body = resp.stream.read()

    assert body.decode() == normalize_path('/var/www/statics/css/test.css')


def test_lifo(client, patch_open):
    patch_open()

    client.app.add_static_route('/downloads', '/opt/somesite/downloads')
    client.app.add_static_route('/downloads/archive', '/opt/somesite/x')

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == normalize_path('/opt/somesite/downloads/thing.zip')

    response = client.simulate_request(path='/downloads/archive/thingtoo.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == normalize_path('/opt/somesite/x/thingtoo.zip')


def test_lifo_negative(client, patch_open):
    patch_open()

    client.app.add_static_route('/downloads/archive', '/opt/somesite/x')
    client.app.add_static_route('/downloads', '/opt/somesite/downloads')

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == normalize_path('/opt/somesite/downloads/thing.zip')

    response = client.simulate_request(path='/downloads/archive/thingtoo.zip')
    assert response.status == falcon.HTTP_200
    assert response.text == normalize_path(
        '/opt/somesite/downloads/archive/thingtoo.zip'
    )


def test_downloadable(client, patch_open):
    patch_open()

    client.app.add_static_route(
        '/downloads', '/opt/somesite/downloads', downloadable=True
    )
    client.app.add_static_route('/assets/', '/opt/somesite/assets')

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_200
    assert response.headers['Content-Disposition'] == 'attachment; filename="thing.zip"'

    response = client.simulate_request(path='/downloads/Some Report.zip')
    assert response.status == falcon.HTTP_200
    assert (
        response.headers['Content-Disposition']
        == 'attachment; filename="Some Report.zip"'
    )

    response = client.simulate_request(path='/assets/css/main.css')
    assert response.status == falcon.HTTP_200
    assert 'Content-Disposition' not in response.headers


def test_downloadable_not_found(client):
    client.app.add_static_route(
        '/downloads', '/opt/somesite/downloads', downloadable=True
    )

    response = client.simulate_request(path='/downloads/thing.zip')
    assert response.status == falcon.HTTP_404


@pytest.mark.parametrize(
    'uri, default, expected, content_type',
    [
        ('', 'default', 'default', 'application/octet-stream'),
        ('other', 'default.html', 'default.html', 'text/html'),
        ('zip', 'default.zip', 'default.zip', 'application/zip'),
        ('index2', 'index', 'index2', 'application/octet-stream'),
        ('absolute', '/foo/bar/index', '/foo/bar/index', 'application/octet-stream'),
        ('docs/notes/test.txt', 'index.html', 'index.html', 'text/html'),
        (
            'index.html_files/test.txt',
            'index.html',
            'index.html_files/test.txt',
            'text/plain',
        ),
    ],
)
@pytest.mark.parametrize('downloadable', [True, False])
def test_fallback_filename(
    asgi,
    util,
    uri,
    default,
    expected,
    content_type,
    downloadable,
    patch_open,
    monkeypatch,
):
    def validate(path):
        if normalize_path(default) not in path:
            raise IOError()

    patch_open(validate=validate)

    monkeypatch.setattr('os.path.isfile', lambda file: normalize_path(default) in file)

    sr = create_sr(
        asgi,
        '/static',
        '/var/www/statics',
        downloadable=downloadable,
        fallback_filename=default,
    )

    req_path = '/static/' + uri

    req = util.create_req(asgi, host='test.com', path=req_path, root_path='statics')
    resp = util.create_resp(asgi)

    if asgi:

        async def run():
            await sr(req, resp)
            return await resp.stream.read()

        body = falcon.async_to_sync(run)
    else:
        sr(req, resp)
        body = resp.stream.read()

    assert sr.match(req.path)
    expected_content = normalize_path(os.path.join('/var/www/statics', expected))
    assert body.decode() == expected_content
    assert resp.content_type in _MIME_ALTERNATIVE.get(content_type, (content_type,))
    assert resp.headers.get('accept-ranges') == 'bytes'

    if downloadable:
        assert os.path.basename(expected) in resp.downloadable_as
    else:
        assert resp.downloadable_as is None


@pytest.mark.parametrize('strip_slash', [True, False])
@pytest.mark.parametrize(
    'path, fallback, static_exp, assert_axp',
    [
        ('/index', 'index.html', 'index', 'index'),
        ('', 'index.html', 'index.html', None),
        ('/', 'index.html', 'index.html', None),
        ('/other', 'index.html', 'index.html', None),
        ('/other', 'index.raise', None, None),
    ],
)
def test_e2e_fallback_filename(
    client, patch_open, monkeypatch, strip_slash, path, fallback, static_exp, assert_axp
):
    def validate(path):
        if 'index' not in path or 'raise' in path:
            raise IOError()

    patch_open(validate=validate)

    monkeypatch.setattr('os.path.isfile', lambda file: 'index' in file)

    client.app.req_options.strip_url_path_trailing_slash = strip_slash
    client.app.add_static_route(
        '/static', '/opt/somesite/static', fallback_filename=fallback
    )
    client.app.add_static_route('/assets/', '/opt/somesite/assets')

    def test(prefix, directory, expected):
        response = client.simulate_request(path=prefix + path)
        if expected is None:
            assert response.status == falcon.HTTP_404
        else:
            assert response.status == falcon.HTTP_200
            assert response.text == normalize_path(directory + expected)
            assert int(response.headers['Content-Length']) == len(response.text)

    test('/static', '/opt/somesite/static/', static_exp)
    test('/assets', '/opt/somesite/assets/', assert_axp)


@pytest.mark.parametrize(
    'default, path, expected',
    [
        (None, '/static', False),
        (None, '/static/', True),
        (None, '/staticfoo', False),
        (None, '/static/foo', True),
        ('index2', '/static', True),
        ('index2', '/static/', True),
        ('index2', '/staticfoo', False),
        ('index2', '/static/foo', True),
    ],
)
def test_match(asgi, default, path, expected, monkeypatch):
    monkeypatch.setattr('os.path.isfile', lambda file: True)
    sr = create_sr(asgi, '/static', '/var/www/statics', fallback_filename=default)

    assert sr.match(path) == expected


def test_filesystem_traversal_fuse(client, monkeypatch):
    def suspicious_normpath(path):
        return 'assets/../../../../' + path

    client.app.add_static_route('/static', '/etc/nginx/includes/static-data')
    monkeypatch.setattr('os.path.normpath', suspicious_normpath)
    response = client.simulate_request(path='/static/shadow')
    assert response.status == falcon.HTTP_404


def test_bounded_file_wrapper():
    buffer = io.BytesIO(b'0123456789')
    fh = _BoundedFile(buffer, 4)
    assert fh.read() == b'0123'
    assert fh.read() == b''
    fh = _BoundedFile(buffer, 4)
    assert list(iter(lambda: fh.read(3), b'')) == [b'456', b'7']
    assert not buffer.closed
    fh.close()
    assert buffer.closed


def test_file_closed(client, patch_open):
    patch_open(b'test_data')

    client.app.add_static_route('/static', '/var/www/statics')

    resp = client.simulate_request(path='/static/foo/bar.txt')
    assert resp.status_code == 200
    assert resp.text == 'test_data'

    assert patch_open.current_file is not None
    assert patch_open.current_file.closed


def test_options_request(client, patch_open):
    patch_open()

    client.app.add_middleware(falcon.CORSMiddleware())
    client.app.add_static_route('/static', '/var/www/statics')

    resp = client.simulate_options(
        path='/static/foo/bar.txt',
        headers={'Origin': 'localhost', 'Access-Control-Request-Method': 'GET'},
    )
    assert resp.status_code == 200
    assert resp.text == ''
    assert int(resp.headers['Content-Length']) == 0
    assert resp.headers['Access-Control-Allow-Methods'] == 'GET'
