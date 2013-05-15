import falcon
import falcon.testing as testing


class TestQueryParams(testing.TestBase):

    def before(self):
        self.resource = testing.TestResource()
        self.api.add_route('/', self.resource)

    def test_none(self):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        store = {}
        self.assertIs(req.get_param('marker'), None)
        self.assertIs(req.get_param('limit', store), None)
        self.assertNotIn('limit', store)
        self.assertIs(req.get_param_as_int('limit'), None)
        self.assertIs(req.get_param_as_bool('limit'), None)
        self.assertIs(req.get_param_as_list('limit'), None)

    def test_blank(self):
        query_string = 'marker='
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertIs(req.get_param('marker'), None)

        store = {}
        self.assertIs(req.get_param('marker', store=store), None)
        self.assertNotIn('marker', store)

    def test_simple(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        store = {}
        self.assertEquals(req.get_param('marker', store=store) or 'nada',
                          'deadbeef')
        self.assertEquals(req.get_param('limit', store=store) or '0', '25')

        self.assertEquals(store['marker'], 'deadbeef')
        self.assertEquals(store['limit'], '25')

    def test_allowed_names(self):
        query_string = ('p=0&p1=23&2p=foo&some-thing=that&blank=&some_thing=x&'
                        '-bogus=foo')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('p'), '0')
        self.assertEquals(req.get_param('p1'), '23')
        self.assertIs(req.get_param('2p'), None)
        self.assertEquals(req.get_param('some-thing'), 'that')
        self.assertIs(req.get_param('blank'), None)
        self.assertEquals(req.get_param('some_thing'), 'x')
        self.assertIs(req.get_param('-bogus'), None)

    def test_required(self):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertRaises(falcon.HTTPBadRequest, req.get_param,
                          'marker', required=True)
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_int,
                          'marker', required=True)
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_bool,
                          'marker', required=True)
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_list,
                          'marker', required=True)

    def test_int(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_int,
                          'marker')

        self.assertEquals(req.get_param_as_int('limit'), 25)

        store = {}
        self.assertEquals(req.get_param_as_int('limit', store=store), 25)
        self.assertEquals(store['limit'], 25)

        self.assertEquals(
            req.get_param_as_int('limit', min=1, max=50), 25)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=0, max=10)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=0, max=24)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=30, max=24)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=30, max=50)

        self.assertEquals(
            req.get_param_as_int('limit', min=1), 25)

        self.assertEquals(
            req.get_param_as_int('limit', max=50), 25)

        self.assertEquals(
            req.get_param_as_int('limit', max=25), 25)

        self.assertEquals(
            req.get_param_as_int('limit', max=26), 25)

        self.assertEquals(
            req.get_param_as_int('limit', min=25), 25)

        self.assertEquals(
            req.get_param_as_int('limit', min=24), 25)

        self.assertEquals(
            req.get_param_as_int('limit', min=-24), 25)

    def test_int_neg(self):
        query_string = 'marker=deadbeef&pos=-7'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param_as_int('pos'), -7)

        self.assertEquals(
            req.get_param_as_int('pos', min=-10, max=10), -7)

        self.assertEquals(
            req.get_param_as_int('pos', max=10), -7)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=-6, max=0)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=-6)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=0, max=10)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=0, max=10)

    def test_boolean(self):
        query_string = ('echo=true&doit=false&bogus=0&bogus2=1&'
                        't1=True&f1=False&t2=yes&f2=no')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_bool,
                          'bogus')
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_bool,
                          'bogus2')

        self.assertEquals(req.get_param_as_bool('echo'), True)
        self.assertEquals(req.get_param_as_bool('doit'), False)

        self.assertEquals(req.get_param_as_bool('t1'), True)
        self.assertEquals(req.get_param_as_bool('t2'), True)
        self.assertEquals(req.get_param_as_bool('f1'), False)
        self.assertEquals(req.get_param_as_bool('f2'), False)

        store = {}
        self.assertEquals(req.get_param_as_bool('echo', store=store), True)
        self.assertEquals(store['echo'], True)

    def test_list_type(self):
        query_string = 'colors=red,green,blue&limit=1'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('colors'), 'red,green,blue')
        self.assertEquals(req.get_param_as_list('colors'),
                          ['red', 'green', 'blue'])
        self.assertEquals(req.get_param_as_list('limit'), ['1'])
        self.assertIs(req.get_param_as_list('marker'), None)

        store = {}
        self.assertEquals(req.get_param_as_list('limit', store=store), ['1'])
        self.assertEquals(store['limit'], ['1'])

    def test_list_transformer(self):
        query_string = 'coord=1.4,13,15.1&limit=100'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param('coord'), '1.4,13,15.1')

        expected = [1.4, 13.0, 15.1]
        actual = req.get_param_as_list('coord', transform=float)
        self.assertEquals(actual, expected)

        self.assertRaises(falcon.HTTPBadRequest,
                          req.get_param_as_list, 'coord', transform=int)

    def test_bogus_input(self):
        query_string = 'colors=red,green,&limit=1&pickle'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEquals(req.get_param_as_list('colors'),
                          ['red', 'green', ''])
        self.assertEquals(req.get_param('limit'), '1')
        self.assertIs(req.get_param('pickle'), None)
