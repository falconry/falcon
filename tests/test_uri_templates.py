import falcon.testsuite as testsuite


class IDResource(object):
    def __init__(self):
        self.id = None
        self.name = None
        self.called = False

    def on_get(self, req, resp, id, name=None):
        self.id = id
        self.name = name
        self.called = True


class TestUriTemplates(testsuite.TestSuite):

    def prepare(self):
        self.resource = testsuite.TestResource()

    def test_root_path(self):
        self.api.add_route('/', self.resource)
        self._simulate_request('/')

        self.assertTrue(self.resource.called)
        req = self.resource.req

        self.assertEquals(req.get_param('id'), None)

    def test_no_vars(self):
        self.api.add_route('/hello/world', self.resource)
        self._simulate_request('/hello/world')

        self.assertTrue(self.resource.called)
        req = self.resource.req

        self.assertEquals(req.get_param('world'), None)

    def test_special_chars(self):
        self.api.add_route('/hello/world.json', self.resource)
        self.api.add_route('/hello(world)', self.resource)

        self._simulate_request('/hello/world_json')
        self.assertFalse(self.resource.called)

        self._simulate_request('/helloworld')
        self.assertFalse(self.resource.called)

        self._simulate_request('/hello/world.json')
        self.assertTrue(self.resource.called)

    def test_single(self):
        self.api.add_route('/widgets/{id}', self.resource)

        self._simulate_request('/widgets/123')
        self.assertTrue(self.resource.called)

        req = self.resource.req
        kwargs = self.resource.kwargs
        self.assertEquals(kwargs['id'], '123')
        self.assertNotIn(kwargs, 'Id')
        self.assertEquals(req.get_param('id'), None)

    def test_single_trailing_slash(self):
        resource = IDResource()
        self.api.add_route('/widgets/{id}/', resource)

        self._simulate_request('/widgets/123')
        self.assertFalse(resource.called)

        self._simulate_request('/widgets/123/')
        self.assertTrue(resource.called)

        self.assertEquals(resource.id, '123')
        self.assertEquals(resource.name, None)

    def test_multiple(self):
        resource = IDResource()
        self.api.add_route('/messages/{id}/names/{name}', resource)

        test_id = self.getUniqueString()
        test_name = self.getUniqueString()
        path = '/messages/' + test_id + '/names/' + test_name
        self._simulate_request(path)
        self.assertTrue(resource.called)

        self.assertEquals(resource.id, test_id)
        self.assertEquals(resource.name, test_name)
