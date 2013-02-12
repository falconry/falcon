import random
import io
import sys
from datetime import datetime

import testtools
import six

import falcon


def httpnow():
    """Returns the current UTC time as an HTTP date

    Returns:
        An HTTP date string, e.g., "Tue, 15 Nov 1994 12:45:26 GMT". See
        also: http://goo.gl/R7So4

    """

    return falcon.dt_to_http(datetime.utcnow())


def rand_string(min, max):
    """Returns a randomly-generated string, of a random length

    Args:
        min: Minimum string length to return, inclusive
        max: Maximum string length to return, inclusive

    """

    int_gen = random.randint
    string_length = int_gen(min, max)
    return ''.join([chr(int_gen(ord('\t'), ord('~')))
                    for i in range(string_length)])


class StartResponseMock:
    """Mock object that represents a WSGI start_response callable

    Attributes:
        call_count: Number of times start_response was called.
        status: HTTP status line, e.g. "785 TPS Cover Sheet not attached".
        headers: Headers array passed to start_response, per PEP-333
        headers_dict: Headers array parsed into a dict to facilitate lookups

    """

    def __init__(self):
        """Initialize attributes to default values"""

        self._called = 0
        self.status = None
        self.headers = None

    def __call__(self, status, headers):
        """Implements the PEP-333 start_response protocol"""

        self._called += 1
        self.status = status
        self.headers = headers
        self.headers_dict = dict(headers)

    @property
    def call_count(self):
        return self._called


class TestResource:
    """Falcon test resource.

    Implements on_get only, and captures request data, as well as
    sets resp body and some sample headers.

    Attributes:
        sample_status: HTTP status set on the response
        sample_body: Random body string set on the response
        resp_headers: Sample headers set on the response

        req: Request passed into the on_get responder
        resp: Response passed into the on_get responder
        kwargs: Keyword arguments (URI fields) passed into the on_get responder
        called: True if on_get was ever called; False otherwise


    """

    sample_status = "200 OK"
    sample_body = rand_string(0, 128 * 1024)
    resp_headers = {
        'Content-Type': 'text/plain; charset=utf-8',
        'ETag': '10d4555ebeb53b30adf724ca198b32a2',
        'X-Hello': 'OH HAI'
    }

    def __init__(self):
        """Initializes called to False"""

        self.called = False

    def on_get(self, req, resp, **kwargs):
        """GET responder

        Captures req, resp, and kwargs. Also sets up a sample response.

        Args:
            req: Falcon Request instance
            resp: Falcon Response instance
            kwargs: URI template name=value pairs

        """

        # Don't try this at home - classes aren't recreated
        # for every request
        self.req, self.resp, self.kwargs = req, resp, kwargs

        self.called = True
        resp.status = falcon.HTTP_200
        resp.body = self.sample_body
        resp.set_headers(self.resp_headers)


class TestSuite(testtools.TestCase):
    """ Creates a basic TestSuite for testing an API endpoint.

    Inherit from this and write your test methods. If the child class defines
    a prepare(self) method, this method will be called before executing each
    test method.

    Attributes:
        api: falcon.API instance used in simulating requests.
        srmock: falcon.testing.StartResponseMock instance used in
            simulating requests.
        test_route: Randomly-generated route string (path) that tests can
            use when wiring up resources.


    """

    def setUp(self):
        """Initializer, unittest-style"""

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

        Args:
            path: Request path for the desired resource
            kwargs: Same as falcon.testing.create_environ()

        """

        if not path:
            path = '/'

        return self.api(create_environ(path=path, **kwargs),
                        self.srmock)


def create_environ(path='/', query_string='', protocol='HTTP/1.1', port='80',
                   headers=None, app='', body='', method='GET',
                   wsgierrors=None):

    """ Creates a 'mock' PEP-333 environ dict for simulating WSGI requests

    Args:
        path: The path for the request (default '/')
        query_string: The query string to simulate (default '')
        protocol: The HTTP protocol to simulate (default 'HTTP/1.1')
        port: The TCP port to simulate (default '80')
        headers: Optional headers to set (default None)
        app: Value for the SCRIPT_NAME environ variable, described in
            PEP-333: 'The initial portion of the request URL's "path" that
            corresponds to the application object, so that the application
            knows its virtual "location". This may be an empty string, if the
            application corresponds to the "root" of the server.' (default '')
        body: The body of the request (default '')
        method: The HTTP method to use (default 'GET')
        wsgierrors: The stream to use as wsgierrors (default sys.stderr)

    """

    body = io.BytesIO(body.encode('utf-8')
                      if isinstance(body, six.text_type) else body)

    env = {
        'SERVER_PROTOCOL': protocol,
        'SERVER_SOFTWARE': 'gunicorn/0.17.0',
        'SCRIPT_NAME': app,
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
