import random
import falcon
from falcon.api import RootedAPI, child
import falcon.testing as testing


class NotFound:
    def _oops(self, request, response):
        raise falcon.HTTPError(falcon.HTTP_404, None)

    on_get = _oops
    on_post = _oops
    on_put = _oops
    on_patch = _oops
    on_delete = _oops

class One:
    @child()
    def two(self, request, segments):
        return Two()

    def on_get(self, request, response):
        response.status = falcon.HTTP_200
        response.body = 'one'

class Two:
    def on_get(self, request, response):
        response.status = falcon.HTTP_200
        response.body = 'two'

class Three:
    def on_get(self, request, response):
        response.status = falcon.HTTP_200
        response.body = 'three'

class Four:
    def on_get(self, request, response):
        response.status = falcon.HTTP_200
        response.body = 'four'

def matcher(request, segments):
    if 'token' in segments:
        # It matches, return positional args, keyword args, and segments.
        return ('ant', 'bee'), dict(cat='cat', dog='dog'), ()
    return None

class Matched:
    def __init__(self, a, b, cat='elk', dog='fly'):
        self.a = a
        self.b = b
        self.c = cat
        self.d = dog

    def on_get(self, request, response):
        response.status = falcon.HTTP_200
        response.body = ''.join((self.a, self.b, self.c, self.d))

class Root:
    @child()
    def one(self, request, segments):
        return One()

    @child('child-o-mine')
    def whatever(self, request, segments):
        return Three()

    @child('^[0-9]+')
    def numbers(self, request, segments):
        return Four()

    @child()
    def consume(self, request, segments):
        segment_count = len(segments)
        next_hop = {
            1: One,
            2: Two,
            3: Three,
            4: Four,
            }.get(segment_count, NotFound)
        # No more path segments.
        return next_hop(), ()

    @child(matcher)
    def matched(self, request, segments, *args, **kws):
        return Matched(*args, **kws)


class TestRootedAPI(testing.TestBase):

    def setUp(self):
        super(TestRootedAPI, self).setUp()
        self.api = RootedAPI(Root())

    def test_child(self):
        response = self.simulate_request('/one/two')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], b'two')

    def test_renamed_child(self):
        response = self.simulate_request('/child-o-mine')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], b'three')

    def test_under_name_not_found(self):
        self.simulate_request('/whatever/two')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_regexp_child(self):
        # Any number works.
        for i in range(4):
            path = '/%03d' % random.randint(0, 999)
            response = self.simulate_request(path)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(response[0], b'four')

    def test_under_regexp_not_found(self):
        self.simulate_request('/numbers')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_path_consumer(self):
        response = self.simulate_request('/consume/a')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], 'one')

        response = self.simulate_request('/consume/a/b')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], 'two')

        response = self.simulate_request('/consume/a/b/c')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], 'three')

        response = self.simulate_request('/consume/a/b/c/d')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], 'four')

        response = self.simulate_request('/consume/a/b/c/d/e')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_callable_matches(self):
        response = self.simulate_request('/this/token/matches')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(response[0], 'antbeecatdog')

    def test_callable_misses(self):
        self.simulate_request('/these/tokens/miss')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)
