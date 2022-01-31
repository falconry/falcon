import hashlib
import os
import random
import subprocess
import sys
import time

import pytest
import requests

from falcon import testing

_HERE = os.path.abspath(os.path.dirname(__file__))
_SERVER_HOST = '127.0.0.1'
_SIZE_1_KB = 1024
_SIZE_1_MB = _SIZE_1_KB**2

_REQUEST_TIMEOUT = 10
_STARTUP_TIMEOUT = 10
_SHUTDOWN_TIMEOUT = 20


def _gunicorn_args(host, port, extra_opts=()):
    """Gunicorn"""
    try:
        import gunicorn  # noqa: F401
    except ImportError:
        pytest.skip('gunicorn not installed')

    args = (
        'gunicorn',
        '--access-logfile',
        '-',
        '--bind',
        '{}:{}'.format(host, port),
        # NOTE(vytas): Although rare, but Meinheld workers have been noticed to
        #   occasionally hang on shutdown.
        '--graceful-timeout',
        str(_SHUTDOWN_TIMEOUT // 2),
        # NOTE(vytas): In case a worker hangs for an unexpectedly long time
        #   while reading or processing request (the default value is 30).
        '--timeout',
        str(_REQUEST_TIMEOUT),
    )
    return args + extra_opts + ('_wsgi_test_app:app',)


def _meinheld_args(host, port):
    """Gunicorn + Meinheld"""
    try:
        import meinheld  # noqa: F401
    except ImportError:
        pytest.skip('meinheld not installed')

    return _gunicorn_args(
        host,
        port,
        (
            '--workers',
            '2',
            '--worker-class',
            'egg:meinheld#gunicorn_worker',
        ),
    )


def _uvicorn_args(host, port):
    """Uvicorn (WSGI interface)"""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        pytest.skip('uvicorn not installed')

    return (
        'uvicorn',
        '--host',
        host,
        '--port',
        str(port),
        '--interface',
        'wsgi',
        '_wsgi_test_app:app',
    )


def _uwsgi_args(host, port):
    """uWSGI"""
    return (
        'uwsgi',
        '--http',
        '{}:{}'.format(host, port),
        '--wsgi-file',
        '_wsgi_test_app.py',
    )


def _waitress_args(host, port):
    """Waitress"""
    try:
        import waitress  # noqa: F401
    except ImportError:
        pytest.skip('waitress not installed')

    return (
        'waitress-serve',
        '--listen',
        '{}:{}'.format(host, port),
        '_wsgi_test_app:app',
    )


@pytest.fixture(params=['gunicorn', 'meinheld', 'uvicorn', 'uwsgi', 'waitress'])
def wsgi_server(request):
    return request.param


@pytest.fixture
def server_args(wsgi_server):
    servers = {
        'gunicorn': _gunicorn_args,
        'meinheld': _meinheld_args,
        'uvicorn': _uvicorn_args,
        'uwsgi': _uwsgi_args,
        'waitress': _waitress_args,
    }
    return servers[wsgi_server]


@pytest.fixture
def server_url(server_args):
    if sys.platform.startswith('win'):
        pytest.skip('WSGI server tests are currently unsupported on Windows')

    for attempt in range(3):
        server_port = testing.get_unused_port()
        base_url = 'http://{}:{}'.format(_SERVER_HOST, server_port)

        args = server_args(_SERVER_HOST, server_port)
        print('Starting {}...'.format(server_args.__doc__))
        print(' '.join(args))
        try:
            server = subprocess.Popen(args, cwd=_HERE)
        except FileNotFoundError:
            pytest.skip('{} executable is not installed'.format(args[0]))

        # NOTE(vytas): give the app server some time to start.
        start_time = time.time()
        while time.time() - start_time < _STARTUP_TIMEOUT:
            try:
                requests.get(base_url + '/hello', timeout=0.2)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                time.sleep(0.2)
            else:
                break
        else:
            if server.poll() is None:
                pytest.fail('Server is not responding to requests')
            else:
                # NOTE(kgriffs): The server did not start up; probably due to
                #   the port being in use. We could check the output but
                #   capsys fixture may not have buffered the error output
                #   yet, so we just retry.
                continue

        yield base_url
        break

    else:
        pytest.fail('Could not start server')

    print('\n[Sending SIGTERM to server process...]')
    server.terminate()

    try:
        server.communicate(timeout=_SHUTDOWN_TIMEOUT)
    except subprocess.TimeoutExpired:
        print('\n[Killing stubborn server process...]')

        server.kill()
        server.communicate()

        pytest.fail(
            'Server process did not exit in a timely manner and had to be killed.'
        )


class TestWSGIServer:
    def test_get(self, server_url):
        resp = requests.get(server_url + '/hello', timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == 'Hello, World!\n'
        assert resp.headers.get('Content-Type') == 'text/plain; charset=utf-8'
        assert resp.headers.get('X-Falcon') == 'peregrine'

    def test_get_deprecated(self, server_url):
        resp = requests.get(server_url + '/deprecated', timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == 'Hello, World!\n'
        assert resp.headers.get('Content-Type') == 'text/plain; charset=utf-8'
        assert resp.headers.get('X-Falcon') == 'deprecated'

    def test_post_multipart_form(self, server_url):
        size = random.randint(8 * _SIZE_1_MB, 15 * _SIZE_1_MB)
        data = os.urandom(size)
        digest = hashlib.sha1(data).hexdigest()
        files = {
            'random': ('random.dat', data),
            'message': ('hello.txt', b'Hello, World!\n'),
        }

        resp = requests.post(
            server_url + '/forms', files=files, timeout=_REQUEST_TIMEOUT
        )
        assert resp.status_code == 200
        assert resp.json() == {
            'message': {
                'filename': 'hello.txt',
                'sha1': '60fde9c2310b0d4cad4dab8d126b04387efba289',
            },
            'random': {
                'filename': 'random.dat',
                'sha1': digest,
            },
        }

    def test_static_file(self, server_url):
        resp = requests.get(
            server_url + '/tests/test_wsgi_servers.py', timeout=_REQUEST_TIMEOUT
        )
        assert resp.status_code == 200

        # TODO(vytas): In retrospect, it would be easier to maintain these
        #   static route tests by creating a separate file instead of relying
        #   on the content of this same __file__.
        assert resp.text.startswith(
            'import hashlib\n'
            'import os\n'
            'import random\n'
            'import subprocess\n'
            'import sys\n'
            'import time\n'
        )
        assert resp.headers.get('Content-Disposition') == (
            'attachment; filename="test_wsgi_servers.py"'
        )

        content_length = int(resp.headers['Content-Length'])
        file_size = os.path.getsize(__file__)
        assert len(resp.content) == content_length == file_size

    @pytest.mark.parametrize(
        'byte_range,expected_head',
        [
            ('7-', b'hashlib'),
            ('2-6', b'port'),
            ('32-38', b'random'),
            ('-47', b'The content of this comment is part of a test.\n'),
        ],
    )
    def test_static_file_byte_range(
        self, byte_range, expected_head, wsgi_server, server_url
    ):
        if wsgi_server == 'meinheld':
            pytest.xfail(
                "Meinheld's file_wrapper fails without a fileno(), see also: "
                'https://github.com/mopemope/meinheld/issues/130'
            )

        resp = requests.get(
            server_url + '/tests/test_wsgi_servers.py',
            timeout=_REQUEST_TIMEOUT,
            headers={'Range': 'bytes=' + byte_range},
        )

        assert resp.status_code == 206
        assert resp.content.startswith(expected_head)

        content_length = int(resp.headers['Content-Length'])
        assert len(resp.content) == content_length

        file_size = os.path.getsize(__file__)
        content_range_size = int(resp.headers['Content-Range'].split('/')[-1])
        assert file_size == content_range_size

        # TODO(vytas): In retrospect, it would be easier to maintain these
        #   static route tests by creating a separate file instead of relying
        #   on the content of this same __file__.

        # NOTE(vytas): The content of this comment is part of a test.
