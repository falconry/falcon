from testtools.matchers import Contains

import falcon
import falcon.testing as testing


class HumanResource(object):
    def on_delete(self, req, resp, name):
        resp.status = falcon.HTTP_204

    def on_get(self, req, resp, name):
        resp.status = falcon.HTTP_402


class UndeadResource(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200


class TestDefaultRouting(testing.TestBase):

    def before(self):
        self.default_resource = UndeadResource()
        self.resource = HumanResource()

    def test_default_only(self):
        self.api.set_default_route(self.default_resource)

        self.simulate_request('/')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        self.simulate_request('/any')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    def test_routing_prioritise(self):
        self.api.set_default_route(self.default_resource)
        self.api.add_route('/people/{name}', self.resource)

        self.simulate_request('/people/asuka')
        self.assertEqual(self.srmock.status, falcon.HTTP_402)

        self.simulate_request('/person/asuka')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        self.simulate_request('/people/asuka', method='DELETE')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_request('/person/asuka', method='DELETE')
        self.assertEqual(self.srmock.status, falcon.HTTP_405)

        headers = self.srmock.headers
        allow_header = ('allow', 'GET, OPTIONS')

        self.assertThat(headers, Contains(allow_header))

        self.simulate_request('/person/asuka', method=self.getUniqueString())
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
