import ddt
import six

import falcon
import falcon.testing as testing


class IDResource(object):
    def __init__(self):
        self.id = None
        self.name = None
        self.called = False

    def on_get(self, req, resp, id):
        self.id = id
        self.called = True
        self.req = req


class NameResource(object):
    def __init__(self):
        self.id = None
        self.name = None
        self.called = False

    def on_get(self, req, resp, id, name):
        self.id = id
        self.name = name
        self.called = True


class NameAndDigitResource(object):
    def __init__(self):
        self.id = None
        self.name51 = None
        self.called = False

    def on_get(self, req, resp, id, name51):
        self.id = id
        self.name51 = name51
        self.called = True


class FileResource(object):
    def __init__(self):
        self.file_id = None
        self.called = False

    def on_get(self, req, resp, file_id):
        self.file_id = file_id
        self.called = True


class FileDetailsResource(object):
    def __init__(self):
        self.file_id = None
        self.ext = None
        self.called = False

    def on_get(self, req, resp, file_id, ext):
        self.file_id = file_id
        self.ext = ext
        self.called = True


@ddt.ddt
class TestUriTemplates(testing.TestBase):

    def before(self):
        self.resource = testing.TestResource()

    def test_root_path(self):
        self.api.add_route('/', self.resource)
        self.simulate_request('/')

        self.assertTrue(self.resource.called)
        req = self.resource.req

        self.assertEqual(req.get_param('id'), None)

    def test_not_str(self):
        self.assertRaises(TypeError, self.api.add_route, {}, self.resource)
        self.assertRaises(TypeError, self.api.add_route, [], self.resource)
        self.assertRaises(TypeError, self.api.add_route, set(), self.resource)
        self.assertRaises(TypeError, self.api.add_route, self, self.resource)

    @ddt.data('/hello/{1world}', '/{524hello}/world')
    def test_field_name_cannot_start_with_digit(self, route):
        self.assertRaises(ValueError, self.api.add_route, route, self.resource)

    @ddt.data(
        '/{thing }/world',
        '/{ thing}/world',
        '/{ thing }/world',
        '/{thing}/wo rld',
        '/{thing} /world'
    )
    def test_whitespace_not_allowed(self, route):
        self.assertRaises(ValueError, self.api.add_route, route, self.resource)

    def test_no_vars(self):
        self.api.add_route('/hello/world', self.resource)
        self.simulate_request('/hello/world')

        self.assertTrue(self.resource.called)
        req = self.resource.req

        self.assertEqual(req.get_param('world'), None)

    def test_unicode_literal_routes(self):
        if six.PY3:
            self.skipTest('Test only applies to Python 2')

        self.api.add_route(u'/hello/world', self.resource)
        self.simulate_request('/hello/world')

        self.assertTrue(self.resource.called)
        req = self.resource.req

        self.assertEqual(req.get_param('world'), None)

    def test_special_chars(self):
        self.api.add_route('/hello/world.json', self.resource)
        self.api.add_route('/hello(world)', self.resource)

        self.simulate_request('/hello/world_json')
        self.assertFalse(self.resource.called)

        self.simulate_request('/helloworld')
        self.assertFalse(self.resource.called)

        self.simulate_request('/hello/world.json')
        self.assertTrue(self.resource.called)

    def test_single(self):
        self.api.add_route('/widgets/{id}', self.resource)

        self.simulate_request('/widgets/123')
        self.assertTrue(self.resource.called)

        req = self.resource.req
        kwargs = self.resource.kwargs
        self.assertEqual(kwargs['id'], '123')
        self.assertNotIn(kwargs, 'Id')
        self.assertEqual(req.get_param('id'), None)

    def test_single_with_trailing_digits(self):
        self.api.add_route('/widgets/{id12}', self.resource)

        self.simulate_request('/widgets/123')
        self.assertTrue(self.resource.called)
        self.assertEqual(self.resource.kwargs['id12'], '123')

    def test_single_with_underscore(self):
        self.api.add_route('/widgets/{widget_id}', self.resource)

        self.simulate_request('/widgets/123')
        self.assertTrue(self.resource.called)
        self.assertEqual(self.resource.kwargs['widget_id'], '123')

    def test_single_trailing_slash(self):
        resource1 = IDResource()
        self.api.add_route('/1/{id}/', resource1)

        self.simulate_request('/1/123')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertTrue(resource1.called)
        self.assertEqual(resource1.id, '123')
        self.assertEqual(resource1.name, None)
        self.assertEqual(resource1.req.path, '/1/123')

        resource2 = IDResource()
        self.api.add_route('/2/{id}/', resource2)

        self.simulate_request('/2/123/')
        self.assertTrue(resource2.called)
        self.assertEqual(resource2.id, '123')
        self.assertEqual(resource2.name, None)
        self.assertEqual(resource2.req.path, '/2/123')

        resource3 = IDResource()
        self.api.add_route('/3/{id}', resource3)

        self.simulate_request('/3/123/')
        self.assertTrue(resource3.called)
        self.assertEqual(resource3.id, '123')
        self.assertEqual(resource3.name, None)
        self.assertEqual(resource3.req.path, '/3/123')

    def test_multiple(self):
        resource = NameResource()
        self.api.add_route('/messages/{id}/names/{name}', resource)

        test_id = self.getUniqueString()
        test_name = self.getUniqueString()
        path = '/messages/' + test_id + '/names/' + test_name
        self.simulate_request(path)
        self.assertTrue(resource.called)

        self.assertEqual(resource.id, test_id)
        self.assertEqual(resource.name, test_name)

    def test_multiple_with_digits(self):
        resource = NameAndDigitResource()
        self.api.add_route('/messages/{id}/names/{name51}', resource)

        test_id = self.getUniqueString()
        test_name = self.getUniqueString()
        path = '/messages/' + test_id + '/names/' + test_name
        self.simulate_request(path)
        self.assertTrue(resource.called)

        self.assertEqual(resource.id, test_id)
        self.assertEqual(resource.name51, test_name)

    @ddt.data('//', '//begin', '/end//', '/in//side')
    def test_empty_path_component(self, route):
        self.assertRaises(ValueError, self.api.add_route, route, self.resource)

    @ddt.data('', 'no', 'no/leading_slash')
    def test_relative_path(self, route):
        self.assertRaises(ValueError, self.api.add_route, route, self.resource)

    def test_same_level_complex_var(self):
        resource = FileResource()
        details_resource = FileDetailsResource()
        self.api.add_route('/files/{file_id}', resource)
        self.api.add_route('/files/{file_id}.{ext}', details_resource)

        # dots cause ambiguous in filenames
        file_id_1 = self.getUniqueString().replace('.', '-')
        file_id_2 = self.getUniqueString().replace('.', '-')
        ext = self.getUniqueString().replace('.', '-')
        path_1 = '/files/' + file_id_1
        path_2 = '/files/' + file_id_2 + '.' + ext

        self.simulate_request(path_1)
        self.assertTrue(resource.called)
        self.assertEqual(resource.file_id, file_id_1)

        self.simulate_request(path_2)
        self.assertTrue(details_resource.called)
        self.assertEqual(details_resource.file_id, file_id_2)
        self.assertEqual(details_resource.ext, ext)

    def test_same_level_complex_var_in_reverse_order(self):
        resource = FileResource()
        details_resource = FileDetailsResource()
        self.api.add_route('/files/{file_id}.{ext}', details_resource)
        self.api.add_route('/files/{file_id}', resource)

        # dots cause ambiguous in filenames
        file_id_1 = self.getUniqueString().replace('.', '-')
        file_id_2 = self.getUniqueString().replace('.', '-')
        ext = self.getUniqueString().replace('.', '-')
        path_1 = '/files/' + file_id_1
        path_2 = '/files/' + file_id_2 + '.' + ext

        self.simulate_request(path_1)
        self.assertTrue(resource.called)
        self.assertEqual(resource.file_id, file_id_1)

        self.simulate_request(path_2)
        self.assertTrue(details_resource.called)
        self.assertEqual(details_resource.file_id, file_id_2)
        self.assertEqual(details_resource.ext, ext)
