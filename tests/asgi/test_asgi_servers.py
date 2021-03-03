import asyncio
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
import websockets
import websockets.exceptions

from falcon import testing
from . import _asgi_test_app


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

    def test_sse_client_disconnects_early(self, server_base_url):
        """Test that when the client connection is lost, the server task does not hang.

        In the case of SSE, Falcon should detect when the client connection is
        lost and immediately bail out. Currently this is observable by watching
        the output of the uvicorn and daphne server processes. Also, the
        _run_server_isolated() method will fail the test if the server process
        takes too long to shut down.
        """
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get(
                server_base_url + 'events',
                timeout=(_asgi_test_app.SSE_TEST_MAX_DELAY_SEC / 2)
            )


class TestWebSocket:

    @pytest.mark.asyncio
    @pytest.mark.parametrize('explicit_close', [True, False])
    @pytest.mark.parametrize('close_code', [None, 4321])
    async def test_hello(self, explicit_close, close_code, server_url_events_ws):
        echo_expected = 'Check 1 - \U0001f600'

        extra_headers = {'X-Command': 'recv'}

        if explicit_close:
            extra_headers['X-Close'] = 'True'

        if close_code:
            extra_headers['X-Close-Code'] = str(close_code)

        async with websockets.connect(
            server_url_events_ws,
            extra_headers=extra_headers,
        ) as ws:
            got_message = False

            while True:
                try:
                    # TODO: Why is this failing to decode on the other side? (raises an error)
                    # TODO: Why does this cause Daphne to hang?
                    await ws.send(f'{{"command": "echo", "echo": "{echo_expected}"}}')

                    message_text = await ws.recv()
                    message_echo = await ws.recv()
                    message_binary = await ws.recv()
                except websockets.exceptions.ConnectionClosed as ex:
                    if explicit_close and close_code:
                        assert ex.code == close_code
                    else:
                        assert ex.code == 1000

                    break

                got_message = True
                assert message_text == 'hello world'
                assert message_echo == echo_expected
                assert message_binary == b'hello\x00world'

            assert got_message

    @pytest.mark.asyncio
    @pytest.mark.parametrize('explicit_close', [True, False])
    @pytest.mark.parametrize('close_code', [None, 4040])
    async def test_rejected(self, explicit_close, close_code, server_url_events_ws):
        extra_headers = {'X-Accept': 'reject'}
        if explicit_close:
            extra_headers['X-Close'] = 'True'

        if close_code:
            extra_headers['X-Close-Code'] = str(close_code)

        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(server_url_events_ws, extra_headers=extra_headers):
                pass

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_responder(self, server_url_events_ws):
        server_url_events_ws += '/404'

        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(server_url_events_ws):
                pass

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize('subprotocol, expected', [
        ('*', 'amqp'),
        ('wamp', 'wamp'),
    ])
    async def test_select_subprotocol_known(self, subprotocol, expected, server_url_events_ws):
        extra_headers = {
            'X-Subprotocol': subprotocol
        }
        async with websockets.connect(
            server_url_events_ws,
            extra_headers=extra_headers,
            subprotocols=['amqp', 'wamp'],
        ) as ws:
            assert ws.subprotocol == expected

    @pytest.mark.asyncio
    async def test_select_subprotocol_unknown(self, server_url_events_ws):
        extra_headers = {
            'X-Subprotocol': 'xmpp'
        }

        try:
            async with websockets.connect(
                server_url_events_ws,
                extra_headers=extra_headers,
                subprotocols=['amqp', 'wamp'],
            ):
                pass

            # NOTE(kgriffs): Taking the approach of asserting inside
            #   except clauses is a little bit cleaner in this case vs.
            #   multiple pytest.raises(), so we fail the test if no
            #   error is raised as expected.
            pytest.fail('no error raised')

        # Uvicorn
        except websockets.exceptions.NegotiationError as ex:
            assert 'unsupported subprotocol: xmpp' in str(ex)

        # Daphne
        except websockets.exceptions.InvalidMessage:
            pass

    # NOTE(kgriffs): When executing this test under pytest with the -s
    #   argument, one should be able to see the message
    #   "on_websocket:WebSocketDisconnected" printed to the console. I have
    #   tried to capture this output and check it in the test below,
    #   but the usual ways of capturing stdout/stderr with pytest do
    #   not work.
    @pytest.mark.asyncio
    async def test_disconnecting_client_early(self, server_url_events_ws):
        ws = await websockets.connect(server_url_events_ws, extra_headers={'X-Close': 'True'})
        await asyncio.sleep(0.2)

        message_text = await ws.recv()
        assert message_text == 'hello world'

        message_binary = await ws.recv()
        assert message_binary == b'hello\x00world'

        await ws.close()
        print('closed')

        # NOTE(kgriffs): Let the app continue to attempt to send us
        #   messages after the close.
        await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_send_before_accept(self, server_url_events_ws):
        extra_headers = {'x-accept': 'skip'}

        async with websockets.connect(server_url_events_ws, extra_headers=extra_headers) as ws:
            message = await ws.recv()
            assert message == 'OperationNotAllowed'

    @pytest.mark.asyncio
    async def test_recv_before_accept(self, server_url_events_ws):
        extra_headers = {'x-accept': 'skip', 'x-command': 'recv'}

        async with websockets.connect(server_url_events_ws, extra_headers=extra_headers) as ws:
            message = await ws.recv()
            assert message == 'OperationNotAllowed'

    @pytest.mark.asyncio
    async def test_invalid_close_code(self, server_url_events_ws):
        extra_headers = {'x-close': 'True', 'x-close-code': 42}

        async with websockets.connect(server_url_events_ws, extra_headers=extra_headers) as ws:
            start = time.time()

            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=1)
                if message == 'ValueError':
                    break

                elapsed = time.time() - start
                assert elapsed < 2

    @pytest.mark.asyncio
    async def test_close_code_on_unhandled_error(self, server_url_events_ws):
        extra_headers = {'x-raise-error': 'generic'}

        async with websockets.connect(server_url_events_ws, extra_headers=extra_headers) as ws:
            await ws.wait_closed()

        assert ws.close_code in {3011, 1011}

    @pytest.mark.asyncio
    async def test_close_code_on_unhandled_http_error(self, server_url_events_ws):
        extra_headers = {'x-raise-error': 'http'}

        async with websockets.connect(server_url_events_ws, extra_headers=extra_headers) as ws:
            await ws.wait_closed()

        assert ws.close_code == 3400

    @pytest.mark.asyncio
    @pytest.mark.parametrize('mismatch', ['send', 'recv'])
    @pytest.mark.parametrize('mismatch_type', ['text', 'data'])
    async def test_type_mismatch(self, mismatch, mismatch_type, server_url_events_ws):
        extra_headers = {
            'X-Mismatch': mismatch,
            'X-Mismatch-Type': mismatch_type,
        }

        async with websockets.connect(server_url_events_ws, extra_headers=extra_headers) as ws:
            if mismatch == 'recv':
                if mismatch_type == 'text':
                    await ws.send(b'hello')
                else:
                    await ws.send('hello')

            await ws.wait_closed()

        assert ws.close_code in {3011, 1011}

    @pytest.mark.asyncio
    async def test_passing_path_params(self, server_base_url_ws):
        expected_feed_id = '1ee7'
        url = f'{server_base_url_ws}feeds/{expected_feed_id}'

        async with websockets.connect(url) as ws:
            feed_id = await ws.recv()
            assert feed_id == expected_feed_id


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
        #   forcefully killing a proc causes the CI job to fail,
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

            pytest.fail('Server process did not exit in a timely manner and had to be killed.')
    else:
        print('\n[Sending SIGTERM to server process...]')
        server.terminate()

        try:
            server.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            print('\n[Killing stubborn server process...]')

            server.kill()
            server.communicate()

            pytest.fail('Server process did not exit in a timely manner and had to be killed.')


def _uvicorn_factory(host, port):
    if _WIN32:
        script = f"""
import uvicorn
import ctypes
ctypes.windll.kernel32.SetConsoleCtrlHandler(None, 0)
uvicorn.run('_asgi_test_app:application', host='{host}', port={port})
"""
        return subprocess.Popen(
            (sys.executable, '-c', script),
            cwd=_MODULE_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    # NOTE(vytas): uvicorn+uvloop is not (well) supported on PyPy at the time
    #   of writing.
    loop_options = ('--http', 'h11', '--loop', 'asyncio') if _PYPY else ()
    options = (
        '--host', host,
        '--port', str(port),

        '--interface', 'asgi3',

        '_asgi_test_app:application'
    )

    return subprocess.Popen(
        ('uvicorn',) + loop_options + options,
        cwd=_MODULE_DIR,
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


def _hypercorn_factory(host, port):
    if _WIN32:
        script = f"""
from hypercorn.run import Config, run
import ctypes
ctypes.windll.kernel32.SetConsoleCtrlHandler(None, 0)
config = Config()
config.application_path = '_asgi_test_app:application'
config.bind = ['{host}:{port}']
config.accesslog = '-'
config.debug = True
run(config)
"""
        return subprocess.Popen(
            (sys.executable, '-c', script),
            cwd=_MODULE_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        (
            'hypercorn',

            '--bind', f'{host}:{port}',

            '--access-logfile', '-',
            '--debug',

            '_asgi_test_app:application'
        ),
        cwd=_MODULE_DIR,
    )


def _can_run(factory):
    if _WIN32 and factory == _daphne_factory:
        pytest.skip('daphne does not support windows')
    if factory == _daphne_factory:
        try:
            import daphne  # noqa
        except Exception:
            pytest.skip('daphne not installed')
    if factory == _hypercorn_factory:
        try:
            import hypercorn  # noqa
        except Exception:
            pytest.skip('hypercorn not installed')


@pytest.fixture(params=[_uvicorn_factory, _daphne_factory, _hypercorn_factory])
def server_base_url(request):
    process_factory = request.param
    _can_run(process_factory)

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


@pytest.fixture
def server_base_url_ws(server_base_url):
    return server_base_url.replace('http', 'ws')


@pytest.fixture
def server_url_events_ws(server_base_url_ws):
    return server_base_url_ws + 'events'
