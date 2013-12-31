import random

from testtools.matchers import Contains

import falcon
import falcon.testing as testing


HTTP_METHODS = list(falcon.HTTP_METHODS)
random.shuffle(HTTP_METHODS)


def unlimited_blade_works(req, resp, invoker):
    pass


class IonioiHetairoi:
    def __call__(self, req, resp):
        pass


class TestHttpMethodProxy(testing.TestBase):

    def before(self):
        self.api.add_proxy('/{invoker}', unlimited_blade_works)
        self.api.add_proxy('/Alexander', IonioiHetairoi(),
                           allow=['GET', 'HEAD'])

    def test_unrestricted_route(self):
        for method in HTTP_METHODS:
            result = self.simulate_request('/Shiro', method=method)

            self.assertEquals(self.srmock.status, falcon.HTTP_200)
            self.assertEquals(result, [])

    def test_restricted_route(self):
        self.simulate_request('/Alexander')
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        # on_options is not added
        self.simulate_request('/Alexander', method='OPTIONS')
        self.assertEquals(self.srmock.status, falcon.HTTP_405)

        headers = self.srmock.headers
        allow_header = ('Allow', 'GET, HEAD')

        self.assertThat(headers, Contains(allow_header))
