import falcon
from falcon import testing


class TestCustomRouter(testing.TestBase):

    def test_custom_router_add_route_should_be_used(self):

        check = []

        class CustomRouter(object):
            def add_route(self, uri_template, *args, **kwargs):
                check.append(uri_template)

        api = falcon.API(router=CustomRouter())
        api.add_route('/test', 'resource')

        self.assertEqual(len(check), 1)
        self.assertIn('/test', check)

    def test_custom_router_find_should_be_used(self):

        def resource(req, resp, **kwargs):
            resp.body = '{"status": "ok"}'

        class CustomRouter(object):
            def __init__(self):
                self.reached_backwards_compat = False

            def find(self, uri):
                if uri == '/test':
                    return resource, {'GET': resource}, {}

                if uri == '/404/backwards-compat':
                    self.reached_backwards_compat = True
                    return (None, None, None)

                return None

        router = CustomRouter()
        self.api = falcon.API(router=router)
        body = self.simulate_request('/test')
        self.assertEqual(body, [b'{"status": "ok"}'])

        for uri in ('/404', '/404/backwards-compat'):
            body = self.simulate_request(uri)
            self.assertFalse(body)
            self.assertEqual(self.srmock.status, falcon.HTTP_404)

        self.assertTrue(router.reached_backwards_compat)

    def test_can_pass_additional_params_to_add_route(self):

        check = []

        class CustomRouter(object):
            def add_route(self, uri_template, method_map, resource, name):
                self._index = {name: uri_template}
                check.append(name)

        api = falcon.API(router=CustomRouter())
        api.add_route('/test', 'resource', name='my-url-name')

        self.assertEqual(len(check), 1)
        self.assertIn('my-url-name', check)

        # Also as arg.
        api.add_route('/test', 'resource', 'my-url-name-arg')

        self.assertEqual(len(check), 2)
        self.assertIn('my-url-name-arg', check)
