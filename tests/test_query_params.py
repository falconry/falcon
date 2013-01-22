from . import helpers


class TestQueryParams(helpers.TestSuite):

    def prepare(self):
        self.resource = helpers.TestResource()
        self.api.add_route('/', self.resource)

    def test_none(self):
        query_string = ''
        self._simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('marker'), None)
        self.assertEquals(req.get_param('limit'), None)

    def test_simple(self):
        query_string = 'marker=deadbeef&limit=25'
        self._simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('marker'), 'deadbeef')
        self.assertEquals(req.get_param('limit'), '25')

    def test_int(self):
        query_string = 'marker=deadbeef&limit=25'
        self._simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param_as_int('marker'), None)
        self.assertEquals(req.get_param_as_int('limit'), 25)

    def test_list_type(self):
        query_string = 'colors=red,green,blue&limit=1'
        self._simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('colors'),
                          ['red', 'green', 'blue'])
        self.assertEquals(req.get_param('limit'), '1')

    def test_bogus_input(self):
        query_string = 'colors=red,green,&limit=1&pickle'
        self._simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('colors'), ['red', 'green', ''])
        self.assertEquals(req.get_param('limit'), '1')
        self.assertEquals(req.get_param('pickle'), None)
