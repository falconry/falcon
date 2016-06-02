import ddt

import falcon
from falcon import routing
import falcon.testing as testing


@ddt.ddt
class TestUriTemplates(testing.TestBase):

    @ddt.data(42, falcon.API)
    def test_string_type_required(self, value):
        self.assertRaises(TypeError, routing.compile_uri_template, value)

    @ddt.data('this', 'this/that')
    def test_template_must_start_with_slash(self, value):
        self.assertRaises(ValueError, routing.compile_uri_template, value)

    @ddt.data('//', 'a//', '//b', 'a//b', 'a/b//', 'a/b//c')
    def test_template_may_not_contain_double_slash(self, value):
        self.assertRaises(ValueError, routing.compile_uri_template, value)

    def test_root(self):
        fields, pattern = routing.compile_uri_template('/')
        self.assertFalse(fields)
        self.assertFalse(pattern.match('/x'))

        result = pattern.match('/')
        self.assertTrue(result)
        self.assertFalse(result.groupdict())

    @ddt.data('/hello', '/hello/world', '/hi/there/how/are/you')
    def test_no_fields(self, path):
        fields, pattern = routing.compile_uri_template(path)
        self.assertFalse(fields)
        self.assertFalse(pattern.match(path[:-1]))

        result = pattern.match(path)
        self.assertTrue(result)
        self.assertFalse(result.groupdict())

    def test_one_field(self):
        fields, pattern = routing.compile_uri_template('/{name}')
        self.assertEqual(fields, set(['name']))

        result = pattern.match('/Kelsier')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'name': 'Kelsier'})

        fields, pattern = routing.compile_uri_template('/character/{name}')
        self.assertEqual(fields, set(['name']))

        result = pattern.match('/character/Kelsier')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'name': 'Kelsier'})

        fields, pattern = routing.compile_uri_template('/character/{name}/profile')
        self.assertEqual(fields, set(['name']))

        self.assertFalse(pattern.match('/character'))
        self.assertFalse(pattern.match('/character/Kelsier'))
        self.assertFalse(pattern.match('/character/Kelsier/'))

        result = pattern.match('/character/Kelsier/profile')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'name': 'Kelsier'})

    def test_one_field_with_digits(self):
        fields, pattern = routing.compile_uri_template('/{name123}')
        self.assertEqual(fields, set(['name123']))

        result = pattern.match('/Kelsier')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'name123': 'Kelsier'})

    def test_one_field_with_prefixed_digits(self):
        fields, pattern = routing.compile_uri_template('/{37signals}')
        self.assertEqual(fields, set())

        result = pattern.match('/s2n')
        self.assertFalse(result)

    @ddt.data('', '/')
    def test_two_fields(self, postfix):
        path = '/book/{book_id}/characters/{n4m3}' + postfix
        fields, pattern = routing.compile_uri_template(path)
        self.assertEqual(fields, set(['n4m3', 'book_id']))

        result = pattern.match('/book/0765350386/characters/Vin')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'n4m3': 'Vin', 'book_id': '0765350386'})

    def test_three_fields(self):
        fields, pattern = routing.compile_uri_template('/{a}/{b}/x/{c}')
        self.assertEqual(fields, set('abc'))

        result = pattern.match('/one/2/x/3')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'a': 'one', 'b': '2', 'c': '3'})

    def test_malformed_field(self):
        fields, pattern = routing.compile_uri_template('/{a}/{1b}/x/{c}')
        self.assertEqual(fields, set('ac'))

        result = pattern.match('/one/{1b}/x/3')
        self.assertTrue(result)
        self.assertEqual(result.groupdict(), {'a': 'one', 'c': '3'})
