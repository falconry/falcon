import test.helpers as helpers


class TestUriTemplates(helpers.TestSuite):

    def prepare(self):
        self.resource = helpers.TestResource()

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

    def test_single(self):
        self.api.add_route('/widgets/{id}', self.resource)

        self._simulate_request('/widgets/123')
        self.assertTrue(self.resource.called)

        req = self.resource.req
        self.assertEquals(req.get_param('id'), '123')
        self.assertEquals(req.get_param('Id'), None)

    def test_single_trailing_slash(self):
        self.api.add_route('/widgets/{id}/', self.resource)

        self._simulate_request('/widgets/123')
        self.assertFalse(self.resource.called)

        self._simulate_request('/widgets/123/')
        self.assertTrue(self.resource.called)

        req = self.resource.req
        self.assertEquals(req.get_param('id'), '123')

    def test_multiple(self):
        self.api.add_route('/messages/{Id}/names/{Name}', self.resource)

        test_id = self.getUniqueString()
        test_name = self.getUniqueString()
        path = '/messages/' + test_id + '/names/' + test_name
        self._simulate_request(path)
        self.assertTrue(self.resource.called)

        req = self.resource.req
        self.assertEquals(req.get_param('Id'), test_id)
        self.assertEquals(req.get_param('Name'), test_name)
        self.assertEquals(req.get_param('name'), None)
