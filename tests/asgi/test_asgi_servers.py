from contextlib import contextmanager
import hashlib
import os
import platform
import random
import subprocess
import sys
import time

import pytest
import requests
import requests.exceptions

from falcon import testing


_MODULE_DIR = os.path.abspath(os.path.dirname(__file__))

_PYPY = platform.python_implementation() == 'PyPy'
_WIN32 = sys.platform.startswith('win')

_SERVER_HOST = '127.0.0.1'
_SIZE_1_KB = 1024
_SIZE_1_MB = _SIZE_1_KB ** 2


_REQUEST_TIMEOUT = 10


class TestASGIServer:

    def test_get(self, server_base_url):
        resp = requests.get(server_base_url, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == '127.0.0.1'

    def test_put(self, server_base_url):
        body = '{}'
        resp = requests.put(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == '{}'

    def test_head_405(self, server_base_url):
        body = '{}'
        resp = requests.head(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 405

    def test_post_multipart_form(self, server_base_url):
        size = random.randint(16 * _SIZE_1_MB, 32 * _SIZE_1_MB)
        data = os.urandom(size)
        digest = hashlib.sha1(data).hexdigest()
        files = {
            'random': ('random.dat', data),
            'message': ('hello.txt', b'Hello, World!\n'),
        }

        resp = requests.post(
            server_base_url + 'forms', files=files, timeout=_REQUEST_TIMEOUT)
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

    def test_post_multiple(self, server_base_url):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == body
        assert resp.headers['X-Counter'] == '0'

        time.sleep(1)

        resp = requests.post(server_base_url, data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.headers['X-Counter'] == '2002'

    def test_post_invalid_content_length(self, server_base_url):
        headers = {'Content-Length': 'invalid'}

        try:
            resp = requests.post(server_base_url, headers=headers, timeout=_REQUEST_TIMEOUT)

            # Daphne responds with a 400
            assert resp.status_code == 400

        except requests.ConnectionError:
            # NOTE(kgriffs): Uvicorn will kill the request so it does not
            #   even get to our app; the app logic is tested on the WSGI
            #   side. We leave this here in case something changes in
            #   the way uvicorn handles it or something and we want to
            #   get a heads-up if the request is no longer blocked.
            pass

    def test_post_read_bounded_stream(self, server_base_url):
        body = testing.rand_string(_SIZE_1_KB / 2, _SIZE_1_KB)
        resp = requests.post(server_base_url + 'bucket', data=body, timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200
        assert resp.text == body

    def test_post_read_bounded_stream_no_body(self, server_base_url):
        resp = requests.post(server_base_url + 'bucket', timeout=_REQUEST_TIMEOUT)
        assert not resp.text

    def test_sse(self, server_base_url):
        resp = requests.get(server_base_url + 'events', timeout=_REQUEST_TIMEOUT)
        assert resp.status_code == 200

        events = resp.text.split('\n\n')
        assert len(events) > 2
        for e in events[:-1]:
            assert e == 'data: hello world'

        assert not events[-1]


@contextmanager
def _run_server_isolated(process_factory, host, port):
    # NOTE(kgriffs): We have to use subprocess because uvicorn has a tendency
    #   to corrupt our asyncio state and cause intermittent hangs in the test
    #   suite.
    print('\n[Starting server process...]')
    server = process_factory(host, port)

    yield server

    if _WIN32:
        # NOTE(kgriffs): Calling server.terminate() is equivalent to
        #   server.kill() on Windows. We don't want to do the this;
        #   forcefully killing a proc causes the Travis job to fail,
        #   regardless of the tox/pytest exit code. """
        #
        #   Instead, we send CTRL+C. This does require that the handler be
        #   enabled via SetConsoleCtrlHandler() in _uvicorn_factory()
        #   below. Alternatively, we could send CTRL+BREAK and allow
        #   the process exit code to be 3221225786.
        #
        import signal
        print('\n[Sending CTRL+C (SIGINT) to server process...]')
        server.send_signal(signal.CTRL_C_EVENT)
        try:
            server.wait(timeout=10)
        except KeyboardInterrupt:
            pass
        except subprocess.TimeoutExpired:
            print('\n[Killing stubborn server process...]')
            server.kill()
            server.communicate()
    else:
        print('\n[Sending SIGTERM to server process...]')
        server.terminate()

        try:
            server.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            print('\n[Killing stubborn server process...]')
            server.kill()
            server.communicate()


def _uvicorn_factory(host, port):
    if _WIN32:
        script = f"""
import uvicorn
import ctypes
ctypes.windll.kernel32.SetConsoleCtrlHandler(None, 0)
uvicorn.run('_asgi_test_app:application', host='{host}', port={port})
"""
        return subprocess.Popen(
            ('python', '-c', script),
            cwd=_MODULE_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    # NOTE(vytas): uvicorn+uvloop is not (well) supported on PyPy at the time
    #   of writing.
    loop_options = ('--http', 'h11', '--loop', 'asyncio') if _PYPY else ()
    options = (
        '--host', host,
        '--port', str(port),

        '_asgi_test_app:application'
    )

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if _WIN32 else 0

    return subprocess.Popen(
        ('uvicorn',) + loop_options + options,
        cwd=_MODULE_DIR,
        creationflags=creationflags,
    )


def _daphne_factory(host, port):
    return subprocess.Popen(
        (
            'daphne',

            '--bind', host,
            '--port', str(port),

            '--verbosity', '2',
            '--access-log', '-',

            '_asgi_test_app:application'
        ),
        cwd=_MODULE_DIR,
    )


@pytest.fixture(params=[_uvicorn_factory, _daphne_factory])
def server_base_url(request):
    process_factory = request.param
    if _WIN32 and process_factory == _daphne_factory:
        pytest.skip('daphne does not support windows')

    for i in range(3):
        server_port = testing.get_unused_port()
        base_url = 'http://{}:{}/'.format(_SERVER_HOST, server_port)

        with _run_server_isolated(process_factory, _SERVER_HOST, server_port) as server:
            # NOTE(kgriffs): Let the server start up. Give up after 5 seconds.
            start_ts = time.time()
            while (time.time() - start_ts) < 5:
                try:
                    requests.get(base_url, timeout=0.2)
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

        assert server.returncode == 0

        break

    else:
        pytest.fail('Could not start server')
