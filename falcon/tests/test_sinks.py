import re

import falcon
import falcon.testing as testing


class Proxy(object):
    def forward(self, req):
        return falcon.HTTP_503


class Sink(object):

    def __init__(self):
        self._proxy = Proxy()

    def __call__(self, req, resp, **kwargs):
        resp.status = self._proxy.forward(req)
        self.kwargs = kwargs


def sink_too(req, resp):
    resp.status = falcon.HTTP_781


class BookCollection(testing.TestResource):
    pass


class TestDefaultRouting(testing.TestBase):

    def before(self):
        self.sink = Sink()
        self.resource = BookCollection()

    def test_single_default_pattern(self):
        self.api.add_sink(self.sink)

        self.simulate_request('/')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

    def test_single_simple_pattern(self):
        self.api.add_sink(self.sink, r'/foo')

        self.simulate_request('/foo/bar')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

    def test_single_compiled_pattern(self):
        self.api.add_sink(self.sink, re.compile(r'/foo'))

        self.simulate_request('/foo/bar')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_request('/auth')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_named_groups(self):
        self.api.add_sink(self.sink, r'/user/(?P<id>\d+)')

        self.simulate_request('/user/309')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)
        self.assertEqual(self.sink.kwargs['id'], '309')

        self.simulate_request('/user/sally')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_multiple_patterns(self):
        self.api.add_sink(self.sink, r'/foo')
        self.api.add_sink(sink_too, r'/foo')  # Last duplicate wins

        self.api.add_sink(self.sink, r'/katza')

        self.simulate_request('/foo/bar')
        self.assertEqual(self.srmock.status, falcon.HTTP_781)

        self.simulate_request('/katza')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

    def test_with_route(self):
        self.api.add_route('/books', self.resource)
        self.api.add_sink(self.sink, '/proxy')

        self.simulate_request('/proxy/books')
        self.assertFalse(self.resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_request('/books')
        self.assertTrue(self.resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    def test_route_precedence(self):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        self.api.add_route('/books', self.resource)
        self.api.add_sink(self.sink, '/books')

        self.simulate_request('/books')
        self.assertTrue(self.resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    def test_route_precedence_with_id(self):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        self.api.add_route('/books/{id}', self.resource)
        self.api.add_sink(self.sink, '/books')

        self.simulate_request('/books')
        self.assertFalse(self.resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

    def test_route_precedence_with_both_id(self):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        self.api.add_route('/books/{id}', self.resource)
        self.api.add_sink(self.sink, '/books/\d+')

        self.simulate_request('/books/123')
        self.assertTrue(self.resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
