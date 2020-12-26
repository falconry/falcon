import io
import sys
import timeit

from .common import get_work_factor

ENVIRON_BOILERPLATE = {
    'HTTP_HOST': 'falconframework.org',
    'PATH_INFO': '/',
    'QUERY_STRING': '',
    'RAW_URI': '/',
    'REMOTE_ADDR': '127.0.0.1',
    'REMOTE_PORT': '61337',
    'REQUEST_METHOD': 'GET',
    'SCRIPT_NAME': '',
    'SCRIPT_NAME': '',
    'SERVER_NAME': 'falconframework.org',
    'SERVER_PORT': '80',
    'SERVER_PROTOCOL': 'HTTP/1.1',
    'SERVER_SOFTWARE': 'falcon/3.0',
    'wsgi.errors': sys.stderr,
    'wsgi.input': io.BytesIO(),
    'wsgi.multiprocess': False,
    'wsgi.multithread': False,
    'wsgi.run_once': False,
    'wsgi.url_scheme': 'http',
    'wsgi.version': (1, 0),
}


def run(app, environ, expected_status, expected_body, number=None):
    def start_response(status, headers, exc_info=None):
        assert status == expected_status

    def request_simple():
        assert b''.join(app(environ, start_response)) == expected_body

    def request_with_payload():
        stream.seek(0)
        assert b''.join(app(environ, start_response)) == expected_body

    environ = dict(ENVIRON_BOILERPLATE, **environ)
    stream = environ['wsgi.input']
    request = request_with_payload if stream.getvalue() else request_simple

    if number is None:
        number = get_work_factor()

    timeit.timeit(request, number=number)
