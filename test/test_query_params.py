import testtools
from testtools.matchers import Equals, Contains, Not

import test.helpers as helpers

class TestQueryParams(helpers.TestSuite):

    def prepare(self):
        self.reqhandler = helpers.RequestHandler()
        self.api.add_route('/', self.reqhandler)

    def test_none(self):
        query_string = ''
        self._simulate_request('/', query_string=query_string)

        req = self.reqhandler.req
        self.assertThat(req.get_param('marker'), Equals(None))
        self.assertThat(req.get_param('limit'), Equals(None))

    def test_simple(self):
        query_string = 'marker=deadbeef&limit=25'
        self._simulate_request('/', query_string=query_string)

        req = self.reqhandler.req
        self.assertThat(req.get_param('marker'), Equals('deadbeef'))
        self.assertThat(req.get_param('limit'), Equals('25'))

    def test_list_type(self):
        query_string = 'colors=red,green,blue&limit=1'
        self._simulate_request('/', query_string=query_string)

        req = self.reqhandler.req
        self.assertThat(req.get_param('colors'), Equals(['red', 'green', 'blue']))
        self.assertThat(req.get_param('limit'), Equals('1'))

    def test_bogus_input(self):
        query_string = 'colors=red,green,&limit=1&pickle'
        self._simulate_request('/', query_string=query_string)

        req = self.reqhandler.req
        self.assertThat(req.get_param('colors'), Equals(['red', 'green', '']))
        self.assertThat(req.get_param('limit'), Equals('1'))
        self.assertThat(req.get_param('pickle'), Equals(None))

