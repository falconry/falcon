import random
import io
import sys
from datetime import datetime

import testtools
import six

import falcon


def httpnow():
    return falcon.dt_to_http(datetime.utcnow())


def rand_string(min, max):
    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord('\t'), ord('~')))
                    for i in range(string_length)])


class StartResponseMock:
    def __init__(self):
        self._called = 0
        self.status = None
        self.headers = None

    def __call__(self, status, headers):
        self._called += 1
        self.status = status
        self.headers = headers
        self.headers_dict = dict(headers)

    def call_count(self):
        return self._called


class TestResource:
    sample_status = "200 OK"
    sample_body = rand_string(0, 128 * 1024)
    resp_headers = {
        'Content-Type': 'text/plain; charset=utf-8',
        'ETag': '10d4555ebeb53b30adf724ca198b32a2',
        'X-Hello': 'OH HAI'
    }

    def __init__(self):
        self.called = False

    def on_get(self, req, resp, **kwargs):
        # Don't try this at home - classes aren't recreated
        # for every request
        self.req, self.resp, self.kwargs = req, resp, kwargs

        self.called = True
        resp.status = falcon.HTTP_200
        resp.body = self.sample_body
        resp.set_headers(self.resp_headers)


class TestSuite(testtools.TestCase):
    """ Creates a basic TestSuite for testing an API endpoint. """

    def setUp(self):
        super(TestSuite, self).setUp()
        self.api = falcon.API()
        self.srmock = StartResponseMock()
        self.test_route = '/' + self.getUniqueString()

        prepare = getattr(self, 'prepare', None)
        if hasattr(prepare, '__call__'):
            prepare()

    def simulate_request(self, path, **kwargs):
        """ Simulates a request.

        Simulates a request to the API for testing purposes.

        See: create_environ() for suitable arguments
        a variable length argument list. See create_environ()
        """

        if not path:
            path = '/'

        return self.api(create_environ(path=path, **kwargs),
                        self.srmock)


def create_environ(path='/', query_string='', protocol='HTTP/1.1', port='80',
                   headers=None, script='', body='', method='GET',
                   wsgierrors=None):

    """ Creates a 'mock' environment for testing

    Args:
        path: The path for the request (default '/')
        query_string: The query string to simulate (default '')
        protocol: The HTTP protocol to simulate (default 'HTTP/1.1')
        port: The TCP port to simulate (default '80')
        headers: Optional headers to set (default None)
        script: The WSGI script name (default '')
        body: The body of the request (default '')
        method: The HTTP method to use (default 'GET')
        wsgierrors: The stream to use as wsgierrors (default sys.stderr)
    """

    body = io.BytesIO(body.encode('utf-8')
                      if isinstance(body, six.text_type) else body)

    env = {
        'SERVER_PROTOCOL': protocol,
        'SERVER_SOFTWARE': 'gunicorn/0.17.0',
        'SCRIPT_NAME': script,
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'HTTP_ACCEPT': '*/*',
        'HTTP_USER_AGENT': ('curl/7.24.0 (x86_64-apple-darwin12.0) '
                            'libcurl/7.24.0 OpenSSL/0.9.8r zlib/1.2.5'),
        'REMOTE_PORT': '65133',
        'RAW_URI': '/',
        'REMOTE_ADDR': '127.0.0.1',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': port,

        'wsgi.url_scheme': 'http',
        'wsgi.input': body,
        'wsgi.errors': wsgierrors or sys.stderr
    }

    if protocol != 'HTTP/1.0':
        env['HTTP_HOST'] = 'falconer'

    if headers is not None:
        for name, value in headers.items():
            name = name.upper().replace('-', '_')

            if value is None:
                if name == 'ACCEPT' or name == 'USER_AGENT':
                    del env['HTTP_' + name]

                continue

            if name == 'CONTENT_TYPE':
                env[name] = value.strip()
            elif name == 'CONTENT_LENGTH':
                env[name] = value.strip()
            else:
                env['HTTP_' + name.upper()] = value.strip()

    return env
