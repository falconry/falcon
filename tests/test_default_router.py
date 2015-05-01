import ddt

import falcon.testing as testing


class ResourceWithId(object):
    def __init__(self, resource_id):
        self.resource_id = resource_id

    def __repr__(self):
        return 'ResourceWithId({0})'.format(self.resource_id)

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

    # NOTE(kgriffs): The ordering of these calls is significant; we
    # need to test that the {id} field does not match the other routes,
    # regardless of the order they are added.
    router_interface.add_route(
        '/emojis/signs/0', {}, ResourceWithId(12))
    router_interface.add_route(
        '/emojis/signs/{id}', {}, ResourceWithId(13))
    router_interface.add_route(
        '/emojis/signs/42', {}, ResourceWithId(14))
    router_interface.add_route(
        '/emojis/signs/42/small', {}, ResourceWithId(14.1))
    router_interface.add_route(
        '/emojis/signs/78/small', {}, ResourceWithId(14.1))

    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/part',
        {}, ResourceWithId(15))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}',
        {}, ResourceWithId(16))
    router_interface.add_route(
        '/repos/{org}/{repo}/compare/{usr0}:{branch0}/full',
        {}, ResourceWithId(17))

    router_interface.add_route(
        '/gists/{id}/raw', {}, ResourceWithId(18))


@ddt.ddt
class TestStandaloneRouter(testing.TestBase):
    def before(self):
        from falcon.routing import DefaultRouter
        self.router = DefaultRouter()
        setup_routes(self.router)

    @ddt.data(
        '/teams/{collision}',
        '/repos/{org}/{repo}/compare/{simple-collision}',
        '/emojis/signs/{id_too}',
    )
    def test_collision(self, template):
        self.assertRaises(
            ValueError,
            self.router.add_route, template, {}, ResourceWithId(-1)
        )

    def test_dump(self):
        print(self.router._src)

    def test_override(self):
        self.router.add_route('/emojis/signs/0', {}, ResourceWithId(-1))

        resource, method_map, params = self.router.find('/emojis/signs/0')
        self.assertEqual(resource.resource_id, -1)

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

    def test_literal_segment(self):
        resource, method_map, params = self.router.find('/emojis/signs/0')
        self.assertEqual(resource.resource_id, 12)

        resource, method_map, params = self.router.find('/emojis/signs/1')
        self.assertEqual(resource.resource_id, 13)

        resource, method_map, params = self.router.find('/emojis/signs/42')
        self.assertEqual(resource.resource_id, 14)

        resource, method_map, params = self.router.find('/emojis/signs/42/small')
        self.assertEqual(resource.resource_id, 14.1)

        resource, method_map, params = self.router.find('/emojis/signs/1/small')
        self.assertEqual(resource, None)

    @ddt.data(
        '/teams',
        '/emojis/signs',
        '/gists',
        '/gists/42',
    )
    def test_dead_segment(self, template):
        resource, method_map, params = self.router.find(template)
        self.assertIs(resource, None)

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

        resource, method_map, params = self.router.find('/emojis/signs/stop')
        self.assertEqual(params, {'id': 'stop'})

        resource, method_map, params = self.router.find('/gists/42/raw')
        self.assertEqual(params, {'id': '42'})

    def test_subsegment_not_found(self):
        resource, method_map, params = self.router.find('/emojis/signs/0/x')
        self.assertIs(resource, None)

    def test_multivar(self):
        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/commits')
        self.assertEqual(resource.resource_id, 4)
        self.assertEqual(params, {'org': 'racker', 'repo': 'falcon'})

        resource, method_map, params = self.router.find(
            '/repos/racker/falcon/compare/all')
        self.assertEqual(resource.resource_id, 11)
        self.assertEqual(params, {'org': 'racker', 'repo': 'falcon'})

    @ddt.data(('', 5), ('/full', 10), ('/part', 15))
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

    @ddt.data(('', 16), ('/full', 17))
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
