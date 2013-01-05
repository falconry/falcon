import inspect
import random

import testtools

import falcon


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


class TestSuite(testtools.TestCase):

    def setUp(self):
        super(TestSuite, self).setUp()
        self.api = falcon.Api()
        self.srmock = StartResponseMock()
        self.test_route = '/' + self.getUniqueString()

        prepare = getattr(self, 'prepare', None)
        if hasattr(prepare, '__call__'):
            prepare()

    def _simulate_request(self, path, protocol='HTTP/1.1', headers=None):
        return self.api(
            create_environ(path=path, protocol=protocol, headers=headers),
            self.srmock)


class RandChars:
    _chars = 'abcdefghijklqmnopqrstuvwxyz0123456789 \n\t!@#$%^&*()-_=+`~<>,.?/'

    def __init__(self, min, max):
        self.target = random.randint(min, max)
        self.counter = 0

    def __iter__(self):
        return self

    def next(self):
        if self.counter < self.target:
            self.counter += 1
            return self._chars[random.randint(0, len(self._chars) - 1)]
        else:
            raise StopIteration


def rand_string(min, max):
    return ''.join([c for c in RandChars(min, max)])


def create_environ(path='/', query_string='',
                   protocol='HTTP/1.1', headers=None):

    env = {
        "SERVER_PROTOCOL": protocol,
        "SERVER_SOFTWARE": "gunicorn/0.17.0",
        "SCRIPT_NAME": "",
        "REQUEST_METHOD": "GET",
        "HTTP_HOST": "localhost:8000",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "HTTP_ACCEPT": "*/*",
        "HTTP_USER_AGENT": ("curl/7.24.0 (x86_64-apple-darwin12.0)"
                            "libcurl/7.24.0 OpenSSL/0.9.8r zlib/1.2.5"),
        "REMOTE_PORT": "65133",
        "RAW_URI": "/",
        "REMOTE_ADDR": "127.0.0.1",
        "wsgi.url_scheme": "http",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8000",
    }

    if headers is not None:
        for name, value in headers.iteritems():
            env['HTTP_' + name.upper()] = value.strip()

    return env
