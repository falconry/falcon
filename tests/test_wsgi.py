import sys
import time
from wsgiref.simple_server import make_server

try:
    import multiprocessing
except ImportError:
    pass  # Jython

import requests
from testtools.matchers import Equals, MatchesRegex

import falcon
import falcon.testing as testing

_SERVER_HOST = 'localhost'
_SERVER_PORT = 9809
_SERVER_BASE_URL = 'http://{0}:{1}/'.format(_SERVER_HOST, _SERVER_PORT)


def _is_iterable(thing):
    try:
        for i in thing:
            break

        return True
    except:
        return False


def _run_server(stop_event):
    class Things(object):
        def on_get(self, req, resp):
            resp.body = req.remote_addr

        def on_post(self, req, resp):
            resp.body = req.stream.read(1000)

        def on_put(self, req, resp):
            # NOTE(kgriffs): Test that reading past the end does
            # not hang.
            req_body = (req.stream.read(1)
                        for i in range(req.content_length + 1))

            resp.body = b''.join(req_body)

    api = application = falcon.API()
    api.add_route('/', Things())

    server = make_server(_SERVER_HOST, _SERVER_PORT, application)

    while not stop_event.is_set():
        server.handle_request()


class TestWSGIInterface(testing.TestBase):

    def test_srmock(self):
        mock = testing.StartResponseMock()
        mock(falcon.HTTP_200, ())

        self.assertEqual(falcon.HTTP_200, mock.status)
        self.assertEqual(None, mock.exc_info)

        mock = testing.StartResponseMock()
        exc_info = sys.exc_info()
        mock(falcon.HTTP_200, (), exc_info)

        self.assertEqual(exc_info, mock.exc_info)

    def test_pep3333(self):
        api = falcon.API()
        mock = testing.StartResponseMock()

        # Simulate a web request (normally done though a WSGI server)
        response = api(testing.create_environ(), mock)

        # Verify that the response is iterable
        self.assertTrue(_is_iterable(response))

        # Make sure start_response was passed a valid status string
        self.assertIs(mock.call_count, 1)
        self.assertTrue(isinstance(mock.status, str))
        self.assertThat(mock.status, MatchesRegex('^\d+[a-zA-Z\s]+$'))

        # Verify headers is a list of tuples, each containing a pair of strings
        self.assertTrue(isinstance(mock.headers, list))
        if len(mock.headers) != 0:
            header = mock.headers[0]
            self.assertTrue(isinstance(header, tuple))
            self.assertThat(len(header), Equals(2))
            self.assertTrue(isinstance(header[0], str))
            self.assertTrue(isinstance(header[1], str))


class TestWSGIReference(testing.TestBase):

    def before(self):
        if 'java' in sys.platform:
            # NOTE(kgriffs): Jython does not support the multiprocessing
            # module. We could alternatively implement these tests
            # using threads, but then we have to force a garbage
            # collection in between each test in order to make
            # the server relinquish its socket, and the gc module
            # doesn't appear to do anything under Jython.
            self.skip('Incompatible with Jython')

        self._stop_event = multiprocessing.Event()
        self._process = multiprocessing.Process(target=_run_server,
                                                args=(self._stop_event,))
        self._process.start()

        # NOTE(kgriffs): Let the server start up
        time.sleep(0.2)

    def after(self):
        self._stop_event.set()

        # NOTE(kgriffs): Pump the request handler loop in case execution
        # made it to the next server.handle_request() before we sent the
        # event.
        try:
            requests.get(_SERVER_BASE_URL)
        except Exception:
            pass  # Thread already exited

        self._process.join()

    def test_wsgiref_get(self):
        resp = requests.get(_SERVER_BASE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, '127.0.0.1')

    def test_wsgiref_put(self):
        body = '{}'
        resp = requests.put(_SERVER_BASE_URL, data=body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, '{}')

    def test_wsgiref_head_405(self):
        body = '{}'
        resp = requests.head(_SERVER_BASE_URL, data=body)
        self.assertEqual(resp.status_code, 405)

    def test_wsgiref_post(self):
        body = '{}'
        resp = requests.post(_SERVER_BASE_URL, data=body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, '{}')

    def test_wsgiref_post_invalid_content_length(self):
        headers = {'Content-Length': 'invalid'}
        resp = requests.post(_SERVER_BASE_URL, headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, '')
