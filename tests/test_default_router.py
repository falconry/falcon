import ddt

import falcon.testing as testing


class ResourceWithId(object):
    def __init__(self, resource_id):
        self.resource_id = resource_id

    def on_get(self, req, resp):
        resp.body = self.resource_id


def setup_routes(router_interface):
    router_interface.add_route(
        '/repos', {}, ResourceWithId(1))
    router_interface.add_route(
        '/repos/{org}', {}, ResourceWithId(2))
    router_interface.add_route(
        '/repos/{org}/{repo}', {}, ResourceWithId(3))
    router_interface.add_route(
        '/repos/{org}/{repo}/commits', {}, ResourceWithId(4))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}',
        {}, ResourceWithId(5))
    router_interface.add_route(
        '/teams/{id}', {}, ResourceWithId(6))
    router_interface.add_route(
        '/teams/{id}/members', {}, ResourceWithId(7))
    router_interface.add_route(
        '/user/memberships', {}, ResourceWithId(8))
    router_interface.add_route(
        '/emojis', {}, ResourceWithId(9))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/full',
        {}, ResourceWithId(10))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/all', {}, ResourceWithId(11))
    router_interface.add_route(
        '/emojis/signs/{id}', {}, ResourceWithId(12))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/part',
        {}, ResourceWithId(13))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}',
        {}, ResourceWithId(14))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}/full',
        {}, ResourceWithId(15))


@ddt.ddt
class TestStandaloneRouter(testing.TestBase):
    def before(self):
        from falcon.routing import DefaultRouter
        self.router = DefaultRouter()
        setup_routes(self.router)

    @ddt.data(
        '/teams/{collision}',
        '/repos/{org}/{repo}/compare/{simple-collision}',
    )
    def test_collision(self, template):
        self.assertRaises(
            ValueError,
            self.router.add_route, template, {}, ResourceWithId(6)
        )

    def test_missing(self):
        resource, method_map, params = self.router.find('/this/does/not/exist')
        self.assertIs(resource, None)

        resource, method_map, params = self.router.find('/user/bogus')
        self.assertIs(resource, None)

        resource, method_map, params = self.router.find('/teams/1234/bogus')
        self.assertIs(resource, None)

        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/compare/johndoe:master...janedoe:dev/bogus')
        self.assertIs(resource, None)

    def test_dead_segment(self):
        resource, method_map, params = self.router.find('/teams')
        self.assertIs(resource, None)

        resource, method_map, params = self.router.find('/emojis/signs')
        self.assertIs(resource, None)

        resource, method_map, params = self.router.find('/emojis/signs/stop')
        self.assertEqual(params, {
            'id': 'stop',
        })

    def test_malformed_pattern(self):
        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/compare/foo')
        self.assertIs(resource, None)

        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/compare/foo/full')
        self.assertIs(resource, None)

    def test_literal(self):
        resource, method_map, params = self.router.find('/user/memberships')
        self.assertEqual(resource.resource_id, 8)

    def test_variable(self):
        resource, method_map, params = self.router.find('/teams/42')
        self.assertEqual(resource.resource_id, 6)
        self.assertEqual(params, {'id': '42'})

    def test_multivar(self):
        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/commits')
        self.assertEqual(resource.resource_id, 4)
        self.assertEqual(params, {'org': 'racker', 'repo': 'falcon'})

        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/compare/all')
        self.assertEqual(resource.resource_id, 11)
        self.assertEqual(params, {'org': 'racker', 'repo': 'falcon'})

    @ddt.data(('', 5), ('/full', 10), ('/part', 13))
    @ddt.unpack
    def test_complex(self, url_postfix, resource_id):
        uri = '/repos/racker/falcon/compare/johndoe:master...janedoe:dev'
        resource, method_map, params = self.router.find(uri + url_postfix)

        self.assertEqual(resource.resource_id, resource_id)
        self.assertEqual(params, {
            'org': 'racker',
            'repo': 'falcon',
            'usr0': 'johndoe',
            'branch0': 'master',
            'usr1': 'janedoe',
            'branch1': 'dev'
        })

    @ddt.data(('', 14), ('/full', 15))
    @ddt.unpack
    def test_complex_alt(self, url_postfix, resource_id):
        uri = '/repos/falconry/falcon/compare/johndoe:master'
        resource, method_map, params = self.router.find(uri + url_postfix)

        self.assertEqual(resource.resource_id, resource_id)
        self.assertEqual(params, {
            'org': 'falconry',
            'repo': 'falcon',
            'usr0': 'johndoe',
            'branch0': 'master',
        })
