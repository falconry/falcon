from datetime import date

import ddt

import falcon
import falcon.testing as testing
from falcon.errors import HTTPInvalidParam
import falcon.request_helpers as helpers


@ddt.ddt
class _TestQueryParams(testing.TestBase):
    param_source = None

    def before(self):
        self.resource = testing.TestResource()
        self.api.add_route('/', self.resource)

    def test_none(self):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        store = {}
        self.assertIs(getter.get('marker'), None)
        self.assertIs(getter.get('limit', store), None)
        self.assertNotIn('limit', store)
        self.assertIs(getter.get_as_int('limit'), None)
        self.assertIs(getter.get_as_bool('limit'), None)
        self.assertIs(getter.get_as_list('limit'), None)

    def test_blank(self):
        query_string = 'marker='
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertIs(getter.get('marker'), None)

        store = {}
        self.assertIs(getter.get('marker', store=store), None)
        self.assertNotIn('marker', store)

    def test_simple(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        store = {}
        self.assertEqual(getter.get('marker', store=store) or 'nada',
                         'deadbeef')
        self.assertEqual(getter.get('limit', store=store) or '0', '25')

        self.assertEqual(store['marker'], 'deadbeef')
        self.assertEqual(store['limit'], '25')

    def test_percent_encoded(self):
        query_string = 'id=23,42&q=%e8%b1%86+%e7%93%a3'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(getter.get('id'), [u'23', u'42'])

        self.assertEqual(getter.get_as_list('id', int), [23, 42])
        self.assertEqual(getter.get('q'), u'\u8c46 \u74e3')

    def test_allowed_names(self):
        query_string = ('p=0&p1=23&2p=foo&some-thing=that&blank=&'
                        'some_thing=x&-bogus=foo&more.things=blah&'
                        '_thing=42&_charset_=utf-8')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertEqual(getter.get('p'), '0')
        self.assertEqual(getter.get('p1'), '23')
        self.assertEqual(getter.get('2p'), 'foo')
        self.assertEqual(getter.get('some-thing'), 'that')
        self.assertIs(getter.get('blank'), None)
        self.assertEqual(getter.get('some_thing'), 'x')
        self.assertEqual(getter.get('-bogus'), 'foo')
        self.assertEqual(getter.get('more.things'), 'blah')
        self.assertEqual(getter.get('_thing'), '42')
        self.assertEqual(getter.get('_charset_'), 'utf-8')

    @ddt.data('get_param', 'get_param_as_int', 'get_param_as_bool',
              'get_param_as_list')
    def test_passthrough_getters(self, method_name):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req

        try:
            getattr(req, method_name)('marker', required=True)
            self.fail('falcon.HTTPMissingParam not raised')
        except falcon.HTTPMissingParam as ex:
            self.assertIsInstance(ex, falcon.HTTPBadRequest)
            self.assertEqual(ex.title, 'Missing parameter')
            expected_desc = 'The "marker" parameter is required.'
            self.assertEqual(ex.description, expected_desc)

    @ddt.data('get', 'get_as_int', 'get_as_bool',
              'get_as_list')
    def test_required(self, method_name):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)

        try:
            getattr(getter, method_name)('marker', required=True)
            self.fail('falcon.HTTPMissingParam not raised')
        except falcon.HTTPMissingParam as ex:
            self.assertEqual(ex.title, 'Missing query parameter')
            expected_desc = 'The "marker" query parameter is required.'
            self.assertEqual(ex.description, expected_desc)

    def test_int(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)

        try:
            getter.get_as_int('marker')
        except Exception as ex:
            self.assertIsInstance(ex, falcon.HTTPBadRequest)
            self.assertIsInstance(ex, falcon.HTTPInvalidParam)
            self.assertEqual(ex.title, 'Invalid parameter')
            expected_desc = ('The "marker" parameter is invalid. '
                             'The value must be an integer.')
            self.assertEqual(ex.description, expected_desc)

        self.assertEqual(getter.get_as_int('limit'), 25)

        store = {}
        self.assertEqual(getter.get_as_int('limit', store=store), 25)
        self.assertEqual(store['limit'], 25)

        self.assertEqual(
            getter.get_as_int('limit', min=1, max=50), 25)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'limit', min=0, max=10)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'limit', min=0, max=24)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'limit', min=30, max=24)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'limit', min=30, max=50)

        self.assertEqual(
            getter.get_as_int('limit', min=1), 25)

        self.assertEqual(
            getter.get_as_int('limit', max=50), 25)

        self.assertEqual(
            getter.get_as_int('limit', max=25), 25)

        self.assertEqual(
            getter.get_as_int('limit', max=26), 25)

        self.assertEqual(
            getter.get_as_int('limit', min=25), 25)

        self.assertEqual(
            getter.get_as_int('limit', min=24), 25)

        self.assertEqual(
            getter.get_as_int('limit', min=-24), 25)

    def test_int_neg(self):
        query_string = 'marker=deadbeef&pos=-7'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertEqual(getter.get_as_int('pos'), -7)

        self.assertEqual(
            getter.get_as_int('pos', min=-10, max=10), -7)

        self.assertEqual(
            getter.get_as_int('pos', max=10), -7)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'pos', min=-6, max=0)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'pos', min=-6)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'pos', min=0, max=10)

        self.assertRaises(
            falcon.HTTPBadRequest,
            getter.get_as_int, 'pos', min=0, max=10)

    def test_boolean(self):
        query_string = ('echo=true&doit=false&bogus=0&bogus2=1&'
                        't1=True&f1=False&t2=yes&f2=no&blank')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertRaises(falcon.HTTPBadRequest, getter.get_as_bool,
                          'bogus')

        try:
            getter.get_as_bool('bogus2')
        except Exception as ex:
            self.assertIsInstance(ex, falcon.HTTPInvalidParam)
            self.assertEqual(ex.title, 'Invalid parameter')
            expected_desc = ('The "bogus2" parameter is invalid. '
                             'The value of the parameter must be "true" '
                             'or "false".')
            self.assertEqual(ex.description, expected_desc)

        self.assertEqual(getter.get_as_bool('echo'), True)
        self.assertEqual(getter.get_as_bool('doit'), False)

        self.assertEqual(getter.get_as_bool('t1'), True)
        self.assertEqual(getter.get_as_bool('t2'), True)
        self.assertEqual(getter.get_as_bool('f1'), False)
        self.assertEqual(getter.get_as_bool('f2'), False)
        self.assertEqual(getter.get('blank'), None)

        store = {}
        self.assertEqual(getter.get_as_bool('echo', store=store), True)
        self.assertEqual(store['echo'], True)

    def test_boolean_blank(self):
        self.api.req_options.keep_blank_qs_values = True
        self.simulate_request(
            '/',
            query_string='blank&blank2=',
        )

        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertEqual(getter.get('blank'), '')
        self.assertEqual(getter.get('blank2'), '')
        self.assertRaises(falcon.HTTPInvalidParam, getter.get_as_bool,
                          'blank')
        self.assertRaises(falcon.HTTPInvalidParam, getter.get_as_bool,
                          'blank2')
        self.assertEqual(getter.get_as_bool('blank', blank_as_true=True),
                         True)
        self.assertEqual(getter.get_as_bool('blank3', blank_as_true=True),
                         None)

    def test_list_type(self):
        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing_one=1,,3'
                        '&thing_two=1&thing_two=&thing_two=3')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(getter.get('colors'), ('red', 'green', 'blue'))

        self.assertEqual(getter.get_as_list('colors'),
                         ['red', 'green', 'blue'])
        self.assertEqual(getter.get_as_list('limit'), ['1'])
        self.assertIs(getter.get_as_list('marker'), None)

        self.assertEqual(getter.get_as_list('empty1'), None)
        self.assertEqual(getter.get_as_list('empty2'), [])
        self.assertEqual(getter.get_as_list('empty3'), [])

        self.assertEqual(getter.get_as_list('list-ish1'),
                         ['f', 'x'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(getter.get_as_list('list-ish2'),
                         ['0'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(getter.get_as_list('list-ish3'),
                         ['a', 'b'])

        # Ensure consistency between list conventions
        self.assertEqual(getter.get_as_list('thing_one'),
                         ['1', '3'])
        self.assertEqual(getter.get_as_list('thing_one'),
                         getter.get_as_list('thing_two'))

        store = {}
        self.assertEqual(getter.get_as_list('limit', store=store), ['1'])
        self.assertEqual(store['limit'], ['1'])

    def test_list_type_blank(self):
        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing_one=1,,3'
                        '&thing_two=1&thing_two=&thing_two=3'
                        '&empty4=&empty4&empty4='
                        '&empty5&empty5&empty5')
        self.api.req_options.keep_blank_qs_values = True
        self.simulate_request(
            '/',
            query_string=query_string
        )

        req = self.resource.req
        getter = getattr(req, self.param_source)

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(getter.get('colors'), ('red', 'green', 'blue'))

        self.assertEqual(getter.get_as_list('colors'),
                         ['red', 'green', 'blue'])
        self.assertEqual(getter.get_as_list('limit'), ['1'])
        self.assertIs(getter.get_as_list('marker'), None)

        self.assertEqual(getter.get_as_list('empty1'), [''])
        self.assertEqual(getter.get_as_list('empty2'), ['', ''])
        self.assertEqual(getter.get_as_list('empty3'), ['', '', ''])

        self.assertEqual(getter.get_as_list('list-ish1'),
                         ['f', '', 'x'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(getter.get_as_list('list-ish2'),
                         ['', '0'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(getter.get_as_list('list-ish3'),
                         ['a', '', '', 'b'])

        # Ensure consistency between list conventions
        self.assertEqual(getter.get_as_list('thing_one'),
                         ['1', '', '3'])
        self.assertEqual(getter.get_as_list('thing_one'),
                         getter.get_as_list('thing_two'))

        store = {}
        self.assertEqual(getter.get_as_list('limit', store=store), ['1'])
        self.assertEqual(store['limit'], ['1'])

        # Test empty elements
        self.assertEqual(getter.get_as_list('empty4'), ['', '', ''])
        self.assertEqual(getter.get_as_list('empty5'), ['', '', ''])
        self.assertEqual(getter.get_as_list('empty4'),
                         getter.get_as_list('empty5'))

    def test_list_transformer(self):
        query_string = 'coord=1.4,13,15.1&limit=100&things=4,,1'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(getter.get('coord'), ('1.4', '13', '15.1'))

        expected = [1.4, 13.0, 15.1]
        actual = getter.get_as_list('coord', transform=float)
        self.assertEqual(actual, expected)

        expected = ['4', '1']
        actual = getter.get_as_list('things', transform=str)
        self.assertEqual(actual, expected)

        expected = [4, 1]
        actual = getter.get_as_list('things', transform=int)
        self.assertEqual(actual, expected)

        try:
            getter.get_as_list('coord', transform=int)
        except Exception as ex:
            self.assertIsInstance(ex, falcon.HTTPInvalidParam)
            self.assertEqual(ex.title, 'Invalid parameter')
            expected_desc = ('The "coord" parameter is invalid. '
                             'The value is not formatted correctly.')
            self.assertEqual(ex.description, expected_desc)

    def test_param_property(self):
        query_string = 'ant=4&bee=3&cat=2&dog=1'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        if self.param_source == 'param':
            params = req.params
        elif self.param_source == 'form_param':
            params = req.form_params

        self.assertEqual(
            sorted(params.items()),
            [('ant', '4'), ('bee', '3'), ('cat', '2'), ('dog', '1')])

    def test_multiple_form_keys(self):
        query_string = 'ant=1&ant=2&bee=3&cat=6&cat=5&cat=4'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        # By definition, we cannot guarantee which of the multiple keys will
        # be returned by .get_param().
        self.assertIn(getter.get('ant'), ('1', '2'))
        # There is only one 'bee' key so it remains a scalar.
        self.assertEqual(getter.get('bee'), '3')
        # There are three 'cat' keys; order is preserved.
        self.assertIn(getter.get('cat'), ('6', '5', '4'))

    def test_multiple_keys_as_bool(self):
        query_string = 'ant=true&ant=yes&ant=True'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertEqual(getter.get_as_bool('ant'), True)

    def test_multiple_keys_as_int(self):
        query_string = 'ant=1&ant=2&ant=3'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.req
        getter = getattr(req, self.param_source)
        self.assertIn(getter.get_as_int('ant'), (1, 2, 3))

    def test_multiple_form_keys_as_list(self):
        query_string = 'ant=1&ant=2&bee=3&cat=6&cat=5&cat=4'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        getter = getattr(req, self.param_source)
        # There are two 'ant' keys.
        self.assertEqual(getter.get_as_list('ant'), ['1', '2'])
        # There is only one 'bee' key..
        self.assertEqual(getter.get_as_list('bee'), ['3'])
        # There are three 'cat' keys; order is preserved.
        self.assertEqual(getter.get_as_list('cat'), ['6', '5', '4'])

    def test_get_date_valid(self):
        date_value = "2015-04-20"
        query_string = "thedate={0}".format(date_value)
        self.simulate_request("/", query_string=query_string)
        req = self.resource.req
        self.assertEqual(req.get_param_as_date("thedate"),
                         date(2015, 4, 20))

    def test_get_date_missing_param(self):
        query_string = "notthedate=2015-04-20"
        self.simulate_request("/", query_string=query_string)
        req = self.resource.req
        self.assertEqual(req.get_param_as_date("thedate"),
                         None)

    def test_get_date_valid_with_format(self):
        date_value = "20150420"
        query_string = "thedate={0}".format(date_value)
        format_string = "%Y%m%d"
        self.simulate_request("/", query_string=query_string)
        req = self.resource.req
        self.assertEqual(req.get_param_as_date("thedate",
                         format_string=format_string),
                         date(2015, 4, 20))

    def test_get_date_store(self):
        date_value = "2015-04-20"
        query_string = "thedate={0}".format(date_value)
        self.simulate_request("/", query_string=query_string)
        req = self.resource.req
        store = {}
        req.get_param_as_date("thedate", store=store)
        self.assertNotEqual(len(store), 0)

    def test_get_date_invalid(self):
        date_value = "notarealvalue"
        query_string = "thedate={0}".format(date_value)
        format_string = "%Y%m%d"
        self.simulate_request("/", query_string=query_string)
        req = self.resource.req
        self.assertRaises(HTTPInvalidParam, req.get_param_as_date,
                          "thedate", format_string=format_string)


class PostQueryParams(_TestQueryParams):
    param_source = "form_param"

    def simulate_request(self, path, query_string, **kwargs):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        super(PostQueryParams, self).simulate_request(
            path, body=query_string, headers=headers, **kwargs)

    def test_non_ascii(self):
        value = u'\u8c46\u74e3'
        query_string = b'q=' + value.encode('utf-8')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        self.assertEqual(req.form_param.get('q'), None)

    def test_dont_consume_body_by_default(self):
        query_string = "foo=bar&baz=quux"
        self.simulate_request("/", query_string=query_string)

        req = self.resource.req
        self.assertNotEqual(req.stream.read(), b"")

    def test_raw_body_data_not_stored(self):
        query_string = "foo=bar&baz=quux"
        self.simulate_request("/", query_string=query_string)

        req = self.resource.req
        self.assertEqual(req.form_param.get("foo"), "bar")
        # With the parameters parsed, the stream (and therefore raw_body)
        # should be empty
        self.assertEqual(req.raw_body, b"")

    def test_raw_body_data_stored(self):
        query_string = "foo=bar&baz=quux"
        self.api.req_options.store_raw_body = True
        self.simulate_request("/", query_string=query_string)

        req = self.resource.req
        self.assertEqual(req.form_param.get("foo"), "bar")
        self.assertNotEqual(req.raw_body, b"")

    def test_unsupported_body_with_form_params(self):
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Transfer-Encoding": "base64"
        }

        body = 'Zm9vPWJhciZiYXo9cXV1eA==\n'
        super(PostQueryParams, self).simulate_request(
            path='/', body=body, headers=headers)

        req = self.resource.req
        self.assertNotEqual(req.raw_body, "")
        self.assertEqual(req.form_param.get("foo"), None)

    def test_unsupported_content_type(self):
        headers = {
            "Content-Type": "image/png",
        }

        body = 'Zm9vPWJhciZiYXo9cXV1eA==\n'
        super(PostQueryParams, self).simulate_request(
            path='/', body=body, headers=headers)

        req = self.resource.req
        self.assertNotEqual(req.raw_body, "")
        self.assertEqual(req.form_param.get("foo"), None)

    def test_unsupported_content_type_with_set_form_param(self):
        headers = {
            "Content-Type": "image/png",
        }

        body = 'Zm9vPWJhciZiYXo9cXV1eA==\n'
        super(PostQueryParams, self).simulate_request(
            path='/', body=body, headers=headers)

        req = self.resource.req
        req._form_param = helpers.ParamProxy(req, req.form_params)
        self.assertNotEqual(req.raw_body, "")
        self.assertEqual(req.form_param.get("foo"), None)

    def test_unsupported_content_type_with_set_form_params(self):
        headers = {
            "Content-Type": "image/png",
        }

        body = 'Zm9vPWJhciZiYXo9cXV1eA==\n'
        super(PostQueryParams, self).simulate_request(
            path='/', body=body, headers=headers)

        req = self.resource.req
        req._form_params = {}
        self.assertNotEqual(req.raw_body, "")
        self.assertEqual(req.form_param.get("foo"), None)


class GetQueryParams(_TestQueryParams):
    param_source = "param"

    def simulate_request(self, path, query_string, **kwargs):
        super(GetQueryParams, self).simulate_request(
            path, query_string=query_string, **kwargs)

    def test_set_form_param(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.req
        req._param = helpers.ParamProxy(req, req.params)
        store = {}
        self.assertEqual(req.param.get('marker', store=store) or 'nada',
                         'deadbeef')
