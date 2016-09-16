import ddt

from falcon.routing import DefaultRouter
import falcon.testing as testing


class ResourceWithId(object):
    def __init__(self, resource_id):
        self.resource_id = resource_id

    def __repr__(self):
        return 'ResourceWithId({0})'.format(self.resource_id)

    def on_get(self, req, resp):
        resp.body = self.resource_id


class TestRegressionCases(testing.TestBase):
    """Test specific repros reported by users of the framework."""

    def before(self):
        self.router = DefaultRouter()

    def test_versioned_url(self):
        self.router.add_route('/{version}/messages', {}, ResourceWithId(2))

        resource, __, __, __ = self.router.find('/v2/messages')
        self.assertEqual(resource.resource_id, 2)

        self.router.add_route('/v2', {}, ResourceWithId(1))

        resource, __, __, __ = self.router.find('/v2')
        self.assertEqual(resource.resource_id, 1)

        resource, __, __, __ = self.router.find('/v2/messages')
        self.assertEqual(resource.resource_id, 2)

        resource, __, __, __ = self.router.find('/v1/messages')
        self.assertEqual(resource.resource_id, 2)

        route = self.router.find('/v1')
        self.assertIs(route, None)

    def test_recipes(self):
        self.router.add_route(
            '/recipes/{activity}/{type_id}', {}, ResourceWithId(1))
        self.router.add_route(
            '/recipes/baking', {}, ResourceWithId(2))

        resource, __, __, __ = self.router.find('/recipes/baking/4242')
        self.assertEqual(resource.resource_id, 1)

        resource, __, __, __ = self.router.find('/recipes/baking')
        self.assertEqual(resource.resource_id, 2)

        route = self.router.find('/recipes/grilling')
        self.assertIs(route, None)


@ddt.ddt
class TestComplexRouting(testing.TestBase):
    def before(self):
        self.router = DefaultRouter()

        self.router.add_route(
            '/repos', {}, ResourceWithId(1))
        self.router.add_route(
            '/repos/{org}', {}, ResourceWithId(2))
        self.router.add_route(
            '/repos/{org}/{repo}', {}, ResourceWithId(3))
        self.router.add_route(
            '/repos/{org}/{repo}/commits', {}, ResourceWithId(4))
        self.router.add_route(
            '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}',
            {}, ResourceWithId(5))

        self.router.add_route(
            '/teams/{id}', {}, ResourceWithId(6))
        self.router.add_route(
            '/teams/{id}/members', {}, ResourceWithId(7))

        self.router.add_route(
            '/teams/default', {}, ResourceWithId(19))
        self.router.add_route(
            '/teams/default/members/thing', {}, ResourceWithId(19))

        self.router.add_route(
            '/user/memberships', {}, ResourceWithId(8))
        self.router.add_route(
            '/emojis', {}, ResourceWithId(9))
        self.router.add_route(
            '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/full',
            {}, ResourceWithId(10))
        self.router.add_route(
            '/repos/{org}/{repo}/compare/all', {}, ResourceWithId(11))

        # NOTE(kgriffs): The ordering of these calls is significant; we
        # need to test that the {id} field does not match the other routes,
        # regardless of the order they are added.
        self.router.add_route(
            '/emojis/signs/0', {}, ResourceWithId(12))
        self.router.add_route(
            '/emojis/signs/{id}', {}, ResourceWithId(13))
        self.router.add_route(
            '/emojis/signs/42', {}, ResourceWithId(14))
        self.router.add_route(
            '/emojis/signs/42/small', {}, ResourceWithId(14.1))
        self.router.add_route(
            '/emojis/signs/78/small', {}, ResourceWithId(22))

        self.router.add_route(
            '/repos/{org}/{repo}/compare/{usr0}:{branch0}...{usr1}:{branch1}/part',
            {}, ResourceWithId(15))
        self.router.add_route(
            '/repos/{org}/{repo}/compare/{usr0}:{branch0}',
            {}, ResourceWithId(16))
        self.router.add_route(
            '/repos/{org}/{repo}/compare/{usr0}:{branch0}/full',
            {}, ResourceWithId(17))

        self.router.add_route(
            '/gists/{id}/{representation}', {}, ResourceWithId(21))
        self.router.add_route(
            '/gists/{id}/raw', {}, ResourceWithId(18))
        self.router.add_route(
            '/gists/first', {}, ResourceWithId(20))

    @ddt.data(
        '/teams/{collision}',  # simple vs simple
        '/emojis/signs/{id_too}',  # another simple vs simple
        '/repos/{org}/{repo}/compare/{complex}:{vs}...{complex2}:{collision}',
    )
    def test_collision(self, template):
        self.assertRaises(
            ValueError,
            self.router.add_route, template, {}, ResourceWithId(-1)
        )

    @ddt.data(
        '/repos/{org}/{repo}/compare/{simple_vs_complex}',
        '/repos/{complex}.{vs}.{simple}',
        '/repos/{org}/{repo}/compare/{complex}:{vs}...{complex2}/full',
    )
    def test_non_collision(self, template):
        self.router.add_route(template, {}, ResourceWithId(-1))

    @ddt.data(
        '/{}',
        '/{9v}',
        '/{@kgriffs}',
        '/repos/{simple-thing}/etc',
        '/repos/{or g}/{repo}/compare/{thing}',
        '/repos/{org}/{repo}/compare/{}',
        '/repos/{complex}.{}.{thing}',
        '/repos/{complex}.{9v}.{thing}/etc',
    )
    def test_invalid_field_name(self, template):
        self.assertRaises(
            ValueError,
            self.router.add_route, template, {}, ResourceWithId(-1))

    def test_dump(self):
        print(self.router._src)

    def test_override(self):
        self.router.add_route('/emojis/signs/0', {}, ResourceWithId(-1))

        resource, __, __, __ = self.router.find('/emojis/signs/0')
        self.assertEqual(resource.resource_id, -1)

    def test_literal_segment(self):
        resource, __, __, __ = self.router.find('/emojis/signs/0')
        self.assertEqual(resource.resource_id, 12)

        resource, __, __, __ = self.router.find('/emojis/signs/1')
        self.assertEqual(resource.resource_id, 13)

        resource, __, __, __ = self.router.find('/emojis/signs/42')
        self.assertEqual(resource.resource_id, 14)

        resource, __, __, __ = self.router.find('/emojis/signs/42/small')
        self.assertEqual(resource.resource_id, 14.1)

        route = self.router.find('/emojis/signs/1/small')
        self.assertEqual(route, None)

    @ddt.data(
        '/teams',
        '/emojis/signs',
        '/gists',
        '/gists/42',
    )
    def test_dead_segment(self, template):
        route = self.router.find(template)
        self.assertIs(route, None)

    def test_malformed_pattern(self):
        route = self.router.find(
            '/repos/racker/falcon/compare/foo')
        self.assertIs(route, None)

        route = self.router.find(
            '/repos/racker/falcon/compare/foo/full')
        self.assertIs(route, None)

    def test_literal(self):
        resource, __, __, __ = self.router.find('/user/memberships')
        self.assertEqual(resource.resource_id, 8)

    def test_variable(self):
        resource, __, params, __ = self.router.find('/teams/42')
        self.assertEqual(resource.resource_id, 6)
        self.assertEqual(params, {'id': '42'})

        __, __, params, __ = self.router.find('/emojis/signs/stop')
        self.assertEqual(params, {'id': 'stop'})

        __, __, params, __ = self.router.find('/gists/42/raw')
        self.assertEqual(params, {'id': '42'})

    @ddt.data(
        ('/teams/default', 19),
        ('/teams/default/members', 7),
        ('/teams/foo', 6),
        ('/teams/foo/members', 7),
        ('/gists/first', 20),
        ('/gists/first/raw', 18),
        ('/gists/first/pdf', 21),
        ('/gists/1776/pdf', 21),
        ('/emojis/signs/78', 13),
        ('/emojis/signs/78/small', 22),
    )
    @ddt.unpack
    def test_literal_vs_variable(self, path, expected_id):
        resource, __, __, __ = self.router.find(path)
        self.assertEqual(resource.resource_id, expected_id)

    @ddt.data(
        # Misc.
        '/this/does/not/exist',
        '/user/bogus',
        '/repos/racker/falcon/compare/johndoe:master...janedoe:dev/bogus',

        # Literal vs variable (teams)
        '/teams',
        '/teams/42/members/undefined',
        '/teams/42/undefined',
        '/teams/42/undefined/segments',
        '/teams/default/members/undefined',
        '/teams/default/members/thing/undefined',
        '/teams/default/members/thing/undefined/segments',
        '/teams/default/undefined',
        '/teams/default/undefined/segments',

        # Literal vs variable (emojis)
        '/emojis/signs',
        '/emojis/signs/0/small',
        '/emojis/signs/0/undefined',
        '/emojis/signs/0/undefined/segments',
        '/emojis/signs/20/small',
        '/emojis/signs/20/undefined',
        '/emojis/signs/42/undefined',
        '/emojis/signs/78/undefined',
    )
    def test_not_found(self, path):
        route = self.router.find(path)
        self.assertIs(route, None)

    def test_subsegment_not_found(self):
        route = self.router.find('/emojis/signs/0/x')
        self.assertIs(route, None)

    def test_multivar(self):
        resource, __, params, __ = self.router.find(
            '/repos/racker/falcon/commits')
        self.assertEqual(resource.resource_id, 4)
        self.assertEqual(params, {'org': 'racker', 'repo': 'falcon'})

        resource, __, params, __ = self.router.find(
            '/repos/racker/falcon/compare/all')
        self.assertEqual(resource.resource_id, 11)
        self.assertEqual(params, {'org': 'racker', 'repo': 'falcon'})

    @ddt.data(('', 5), ('/full', 10), ('/part', 15))
    @ddt.unpack
    def test_complex(self, url_postfix, resource_id):
        uri = '/repos/racker/falcon/compare/johndoe:master...janedoe:dev'
        resource, __, params, __ = self.router.find(uri + url_postfix)

        self.assertEqual(resource.resource_id, resource_id)
        self.assertEqual(params, {
            'org': 'racker',
            'repo': 'falcon',
            'usr0': 'johndoe',
            'branch0': 'master',
            'usr1': 'janedoe',
            'branch1': 'dev',
        })

    @ddt.data(
        ('', 16, '/repos/{org}/{repo}/compare/{usr0}:{branch0}'),
        ('/full', 17, '/repos/{org}/{repo}/compare/{usr0}:{branch0}/full')
    )
    @ddt.unpack
    def test_complex_alt(self, url_postfix, resource_id, expected_template):
        uri = '/repos/falconry/falcon/compare/johndoe:master' + url_postfix
        resource, __, params, uri_template = self.router.find(uri)

        self.assertEqual(resource.resource_id, resource_id)
        self.assertEqual(params, {
            'org': 'falconry',
            'repo': 'falcon',
            'usr0': 'johndoe',
            'branch0': 'master',
        })
        self.assertEqual(uri_template, expected_template)
