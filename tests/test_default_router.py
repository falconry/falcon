import falcon.testing as testing

from testtools.matchers import HasLength


class ResourceWithId(object):
    def __init__(self, resource_id):
        self.resource_id = resource_id

    def on_get(self, req, resp):
        resp.body = self.resource_id
        

def setup_routes(router_interface):
    """ Setup som sample routes inspired by the GitHub API. """

    router_interface.add_route('/repos', {}, ResourceWithId(1))
    router_interface.add_route('/repos/{organization}', {}, ResourceWithId(2))
    router_interface.add_route('/repos/{organization}/{repo}', {}, ResourceWithId(3))
    router_interface.add_route('/repos/{organization}/{repo}/commits', {}, ResourceWithId(4))
    router_interface.add_route('/repos/{organization}/{repo}/compare/{user0}:{branch0}...{user1}:{branch1}', {}, ResourceWithId(5))
    router_interface.add_route('/teams/{id}', {}, ResourceWithId(6))
    router_interface.add_route('/teams/{id}/members', {}, ResourceWithId(7))
    router_interface.add_route('/user/memberships', {}, ResourceWithId(8))
    router_interface.add_route('/emojis', {}, ResourceWithId(9))
    router_interface.add_route('/repos/{organization}/{repo}/compare/{user0}:{branch0}...{user1}:{branch1}/full', {}, ResourceWithId(10))
    router_interface.add_route('/repos/{organization}/{repo}/compare/all', {}, ResourceWithId(10))


class TestStandaloneRouter(testing.TestBase):
    def before(self):
        from falcon.routing import DefaultRouter
        self.router = DefaultRouter()
        setup_routes(self.router)

    def test_structure(self):
        self.assertThat(self.router._roots, HasLength(4))
        self.assertThat(self.router._roots[0].children, HasLength(1))
        self.assertThat(self.router._roots[0].children[0].children, HasLength(1))
        self.assertThat(self.router._roots[0].children[0].children[0].children, HasLength(2))
        self.assertThat(self.router._roots[0].children[0].children[0].children[1].children, HasLength(2))
        self.assertThat(self.router._roots[0].children[0].children[0].children[1].children[0].children, HasLength(1))
        self.assertThat(self.router._roots[1].children, HasLength(1))
        self.assertThat(self.router._roots[1].children[0].children, HasLength(1))
        self.assertThat(self.router._roots[2].children, HasLength(1))
        self.assertThat(self.router._roots[3].children, HasLength(0))

    def test_missing(self):
        resource, method_map, params = self.router.find('/this/does/not/exist')
        self.assertIs(resource, None)

    def test_literal(self):
        resource, method_map, params = self.router.find('/user/memberships')
        self.assertEqual(resource.resource_id, 8)
        
    def test_variable(self):
        resource, method_map, params = self.router.find('/teams/42')
        self.assertEqual(resource.resource_id, 6)
        self.assertEqual(params, { 'id': '42' })

    def test_multivar(self):
        resource, method_map, params = self.router.find('/repos/racker/falcon/commits')
        self.assertEqual(resource.resource_id, 4)
        self.assertEqual(params, { 'organization': 'racker', 'repo': 'falcon' })

    def test_complex(self):
        resource, method_map, params = self.router.find('/repos/racker/falcon/compare/johndoe:master...janedoe:dev')
        self.assertEqual(resource.resource_id, 5)
        self.assertEqual(params, {
            'organization': 'racker',
            'repo': 'falcon',
            'user0': 'johndoe',
            'branch0': 'master',
            'user1': 'janedoe',
            'branch1': 'dev'
        })


