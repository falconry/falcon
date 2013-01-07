import testtools
from testtools.matchers import Equals, Contains, Not

import test.helpers as helpers

class TestUriTemplates(helpers.TestSuite):

    def prepare(self):
        self.reqhandler = helpers.RequestHandler()

    def test_root_path(self):
        self.api.add_route('/', self.reqhandler)
        self._simulate_request('/')

        self.assertTrue(self.reqhandler.called)
        req = self.reqhandler.req

        self.assertThat(req.get_param('id'), Equals(None))

    def test_no_vars(self):
        self.api.add_route('/hello/world', self.reqhandler)
        self._simulate_request('/hello/world')

        self.assertTrue(self.reqhandler.called)
        req = self.reqhandler.req

        self.assertThat(req.get_param('world'), Equals(None))

    def test_single(self):
        self.api.add_route('/widgets/{id}', self.reqhandler)

        self._simulate_request('/widgets/123')
        self.assertTrue(self.reqhandler.called)

        req = self.reqhandler.req
        self.assertThat(req.get_param('id'), Equals('123'))
        self.assertThat(req.get_param('Id'), Equals(None))

    def test_single_trailing_slash(self):
        self.api.add_route('/widgets/{id}/', self.reqhandler)

        self._simulate_request('/widgets/123')
        self.assertFalse(self.reqhandler.called)

        self._simulate_request('/widgets/123/')
        self.assertTrue(self.reqhandler.called)

        req = self.reqhandler.req
        self.assertThat(req.get_param('id'), Equals('123'))

    def test_multiple(self):
        self.api.add_route('/messages/{Id}/names/{Name}', self.reqhandler)

        test_id = self.getUniqueString()
        test_name = self.getUniqueString()
        path = '/messages/' + test_id + '/names/' + test_name
        self._simulate_request(path)
        self.assertTrue(self.reqhandler.called)

        req = self.reqhandler.req
        self.assertThat(req.get_param('Id'), Equals(test_id))
        self.assertThat(req.get_param('Name'), Equals(test_name))
        self.assertThat(req.get_param('name'), Equals(None))
