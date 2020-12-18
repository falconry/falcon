import io
import sys

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
