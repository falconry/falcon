from datetime import date
import json

import ddt

import falcon
from falcon.errors import HTTPInvalidParam
import falcon.testing as testing


class Resource(testing.SimpleTestResource):

    @falcon.before(testing.capture_responder_args)
    @falcon.before(testing.set_resp_defaults)
    def on_put(self, req, resp, **kwargs):
        pass

    @falcon.before(testing.capture_responder_args)
    @falcon.before(testing.set_resp_defaults)
    def on_patch(self, req, resp, **kwargs):
        pass

    @falcon.before(testing.capture_responder_args)
    @falcon.before(testing.set_resp_defaults)
    def on_delete(self, req, resp, **kwargs):
        pass

    @falcon.before(testing.capture_responder_args)
    @falcon.before(testing.set_resp_defaults)
    def on_head(self, req, resp, **kwargs):
        pass

    @falcon.before(testing.capture_responder_args)
    @falcon.before(testing.set_resp_defaults)
    def on_options(self, req, resp, **kwargs):
        pass


@ddt.ddt
class _TestQueryParams(testing.TestBase):

    def before(self):
        self.resource = Resource()
        self.api.add_route('/', self.resource)

    def test_none(self):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        store = {}
        self.assertIs(req.get_param('marker'), None)
        self.assertIs(req.get_param('limit', store), None)
        self.assertNotIn('limit', store)
        self.assertIs(req.get_param_as_int('limit'), None)
        self.assertIs(req.get_param_as_bool('limit'), None)
        self.assertIs(req.get_param_as_list('limit'), None)

    def test_blank(self):
        query_string = 'marker='
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        self.assertIs(req.get_param('marker'), None)

        store = {}
        self.assertIs(req.get_param('marker', store=store), None)
        self.assertNotIn('marker', store)

    def test_simple(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        store = {}
        self.assertEqual(req.get_param('marker', store=store) or 'nada',
                         'deadbeef')
        self.assertEqual(req.get_param('limit', store=store) or '0', '25')

        self.assertEqual(store['marker'], 'deadbeef')
        self.assertEqual(store['limit'], '25')

    def test_percent_encoded(self):
        query_string = 'id=23,42&q=%e8%b1%86+%e7%93%a3'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(req.get_param('id'), [u'23', u'42'])

        self.assertEqual(req.get_param_as_list('id', int), [23, 42])
        self.assertEqual(req.get_param('q'), u'\u8c46 \u74e3')

    def test_option_auto_parse_qs_csv_simple_false(self):
        self.api.req_options.auto_parse_qs_csv = False

        query_string = 'id=23,42,,&id=2'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        self.assertEqual(req.params['id'], [u'23,42,,', u'2'])
        self.assertIn(req.get_param('id'), [u'23,42,,', u'2'])
        self.assertEqual(req.get_param_as_list('id'), [u'23,42,,', u'2'])

    def test_option_auto_parse_qs_csv_simple_true(self):
        self.api.req_options.auto_parse_qs_csv = True

        query_string = 'id=23,42,,&id=2'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        self.assertEqual(req.params['id'], [u'23', u'42', u'2'])
        self.assertIn(req.get_param('id'), [u'23', u'42', u'2'])
        self.assertEqual(req.get_param_as_list('id', int), [23, 42, 2])

    def test_option_auto_parse_qs_csv_complex_false(self):
        self.api.req_options.auto_parse_qs_csv = False

        encoded_json = '%7B%22msg%22:%22Testing%201,2,3...%22,%22code%22:857%7D'
        decoded_json = '{"msg":"Testing 1,2,3...","code":857}'

        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing=' + encoded_json)

        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        self.assertIn(req.get_param('colors'), 'red,green,blue')
        self.assertEqual(req.get_param_as_list('colors'), [u'red,green,blue'])

        self.assertEqual(req.get_param_as_list('limit'), ['1'])

        self.assertEqual(req.get_param_as_list('empty1'), None)
        self.assertEqual(req.get_param_as_list('empty2'), [u','])
        self.assertEqual(req.get_param_as_list('empty3'), [u',,'])

        self.assertEqual(req.get_param_as_list('list-ish1'), [u'f,,x'])
        self.assertEqual(req.get_param_as_list('list-ish2'), [u',0'])
        self.assertEqual(req.get_param_as_list('list-ish3'), [u'a,,,b'])

        self.assertEqual(req.get_param('thing'), decoded_json)

    def test_bad_percentage(self):
        query_string = 'x=%%20%+%&y=peregrine&z=%a%z%zz%1%20e'
        self.simulate_request('/', query_string=query_string)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        req = self.resource.captured_req
        self.assertEqual(req.get_param('x'), '% % %')
        self.assertEqual(req.get_param('y'), 'peregrine')
        self.assertEqual(req.get_param('z'), '%a%z%zz%1 e')

    def test_allowed_names(self):
        query_string = ('p=0&p1=23&2p=foo&some-thing=that&blank=&'
                        'some_thing=x&-bogus=foo&more.things=blah&'
                        '_thing=42&_charset_=utf-8')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        self.assertEqual(req.get_param('p'), '0')
        self.assertEqual(req.get_param('p1'), '23')
        self.assertEqual(req.get_param('2p'), 'foo')
        self.assertEqual(req.get_param('some-thing'), 'that')
        self.assertIs(req.get_param('blank'), None)
        self.assertEqual(req.get_param('some_thing'), 'x')
        self.assertEqual(req.get_param('-bogus'), 'foo')
        self.assertEqual(req.get_param('more.things'), 'blah')
        self.assertEqual(req.get_param('_thing'), '42')
        self.assertEqual(req.get_param('_charset_'), 'utf-8')

    @ddt.data('get_param', 'get_param_as_int', 'get_param_as_bool',
              'get_param_as_list')
    def test_required(self, method_name):
        query_string = ''
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        try:
            getattr(req, method_name)('marker', required=True)
            self.fail('falcon.HTTPMissingParam not raised')
        except falcon.HTTPMissingParam as ex:
            self.assertIsInstance(ex, falcon.HTTPBadRequest)
            self.assertEqual(ex.title, 'Missing parameter')
            expected_desc = 'The "marker" parameter is required.'
            self.assertEqual(ex.description, expected_desc)

    def test_int(self):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        try:
            req.get_param_as_int('marker')
        except Exception as ex:
            self.assertIsInstance(ex, falcon.HTTPBadRequest)
            self.assertIsInstance(ex, falcon.HTTPInvalidParam)
            self.assertEqual(ex.title, 'Invalid parameter')
            expected_desc = ('The "marker" parameter is invalid. '
                             'The value must be an integer.')
            self.assertEqual(ex.description, expected_desc)

        self.assertEqual(req.get_param_as_int('limit'), 25)

        store = {}
        self.assertEqual(req.get_param_as_int('limit', store=store), 25)
        self.assertEqual(store['limit'], 25)

        self.assertEqual(
            req.get_param_as_int('limit', min=1, max=50), 25)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=0, max=10)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=0, max=24)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=30, max=24)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'limit', min=30, max=50)

        self.assertEqual(
            req.get_param_as_int('limit', min=1), 25)

        self.assertEqual(
            req.get_param_as_int('limit', max=50), 25)

        self.assertEqual(
            req.get_param_as_int('limit', max=25), 25)

        self.assertEqual(
            req.get_param_as_int('limit', max=26), 25)

        self.assertEqual(
            req.get_param_as_int('limit', min=25), 25)

        self.assertEqual(
            req.get_param_as_int('limit', min=24), 25)

        self.assertEqual(
            req.get_param_as_int('limit', min=-24), 25)

    def test_int_neg(self):
        query_string = 'marker=deadbeef&pos=-7'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_int('pos'), -7)

        self.assertEqual(
            req.get_param_as_int('pos', min=-10, max=10), -7)

        self.assertEqual(
            req.get_param_as_int('pos', max=10), -7)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=-6, max=0)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=-6)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=0, max=10)

        self.assertRaises(
            falcon.HTTPBadRequest,
            req.get_param_as_int, 'pos', min=0, max=10)

    def test_boolean(self):
        query_string = ('echo=true&doit=false&bogus=bar&bogus2=foo&'
                        't1=True&f1=False&t2=yes&f2=no&blank&one=1&zero=0&'
                        'checkbox1=on&checkbox2=off')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        self.assertRaises(falcon.HTTPBadRequest, req.get_param_as_bool,
                          'bogus')

        try:
            req.get_param_as_bool('bogus2')
        except Exception as ex:
            self.assertIsInstance(ex, falcon.HTTPInvalidParam)
            self.assertEqual(ex.title, 'Invalid parameter')
            expected_desc = ('The "bogus2" parameter is invalid. '
                             'The value of the parameter must be "true" '
                             'or "false".')
            self.assertEqual(ex.description, expected_desc)

        self.assertEqual(req.get_param_as_bool('echo'), True)
        self.assertEqual(req.get_param_as_bool('doit'), False)

        self.assertEqual(req.get_param_as_bool('t1'), True)
        self.assertEqual(req.get_param_as_bool('t2'), True)
        self.assertEqual(req.get_param_as_bool('f1'), False)
        self.assertEqual(req.get_param_as_bool('f2'), False)
        self.assertEqual(req.get_param_as_bool('one'), True)
        self.assertEqual(req.get_param_as_bool('zero'), False)
        self.assertEqual(req.get_param('blank'), None)

        self.assertEqual(req.get_param_as_bool('checkbox1'), True)
        self.assertEqual(req.get_param_as_bool('checkbox2'), False)

        store = {}
        self.assertEqual(req.get_param_as_bool('echo', store=store), True)
        self.assertEqual(store['echo'], True)

    def test_boolean_blank(self):
        self.api.req_options.keep_blank_qs_values = True
        self.simulate_request(
            '/',
            query_string='blank&blank2=',
        )

        req = self.resource.captured_req
        self.assertEqual(req.get_param('blank'), '')
        self.assertEqual(req.get_param('blank2'), '')
        self.assertRaises(falcon.HTTPInvalidParam, req.get_param_as_bool,
                          'blank')
        self.assertRaises(falcon.HTTPInvalidParam, req.get_param_as_bool,
                          'blank2')
        self.assertEqual(req.get_param_as_bool('blank', blank_as_true=True),
                         True)
        self.assertEqual(req.get_param_as_bool('blank3', blank_as_true=True),
                         None)

    def test_list_type(self):
        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing_one=1,,3'
                        '&thing_two=1&thing_two=&thing_two=3')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(req.get_param('colors'), ('red', 'green', 'blue'))

        self.assertEqual(req.get_param_as_list('colors'),
                         ['red', 'green', 'blue'])
        self.assertEqual(req.get_param_as_list('limit'), ['1'])
        self.assertIs(req.get_param_as_list('marker'), None)

        self.assertEqual(req.get_param_as_list('empty1'), None)
        self.assertEqual(req.get_param_as_list('empty2'), [])
        self.assertEqual(req.get_param_as_list('empty3'), [])

        self.assertEqual(req.get_param_as_list('list-ish1'),
                         ['f', 'x'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(req.get_param_as_list('list-ish2'),
                         ['0'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(req.get_param_as_list('list-ish3'),
                         ['a', 'b'])

        # Ensure consistency between list conventions
        self.assertEqual(req.get_param_as_list('thing_one'),
                         ['1', '3'])
        self.assertEqual(req.get_param_as_list('thing_one'),
                         req.get_param_as_list('thing_two'))

        store = {}
        self.assertEqual(req.get_param_as_list('limit', store=store), ['1'])
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

        req = self.resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(req.get_param('colors'), ('red', 'green', 'blue'))

        self.assertEqual(req.get_param_as_list('colors'),
                         ['red', 'green', 'blue'])
        self.assertEqual(req.get_param_as_list('limit'), ['1'])
        self.assertIs(req.get_param_as_list('marker'), None)

        self.assertEqual(req.get_param_as_list('empty1'), [''])
        self.assertEqual(req.get_param_as_list('empty2'), ['', ''])
        self.assertEqual(req.get_param_as_list('empty3'), ['', '', ''])

        self.assertEqual(req.get_param_as_list('list-ish1'),
                         ['f', '', 'x'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(req.get_param_as_list('list-ish2'),
                         ['', '0'])

        # Ensure that '0' doesn't get translated to None
        self.assertEqual(req.get_param_as_list('list-ish3'),
                         ['a', '', '', 'b'])

        # Ensure consistency between list conventions
        self.assertEqual(req.get_param_as_list('thing_one'),
                         ['1', '', '3'])
        self.assertEqual(req.get_param_as_list('thing_one'),
                         req.get_param_as_list('thing_two'))

        store = {}
        self.assertEqual(req.get_param_as_list('limit', store=store), ['1'])
        self.assertEqual(store['limit'], ['1'])

        # Test empty elements
        self.assertEqual(req.get_param_as_list('empty4'), ['', '', ''])
        self.assertEqual(req.get_param_as_list('empty5'), ['', '', ''])
        self.assertEqual(req.get_param_as_list('empty4'),
                         req.get_param_as_list('empty5'))

    def test_list_transformer(self):
        query_string = 'coord=1.4,13,15.1&limit=100&things=4,,1'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        self.assertIn(req.get_param('coord'), ('1.4', '13', '15.1'))

        expected = [1.4, 13.0, 15.1]
        actual = req.get_param_as_list('coord', transform=float)
        self.assertEqual(actual, expected)

        expected = ['4', '1']
        actual = req.get_param_as_list('things', transform=str)
        self.assertEqual(actual, expected)

        expected = [4, 1]
        actual = req.get_param_as_list('things', transform=int)
        self.assertEqual(actual, expected)

        try:
            req.get_param_as_list('coord', transform=int)
        except Exception as ex:
            self.assertIsInstance(ex, falcon.HTTPInvalidParam)
            self.assertEqual(ex.title, 'Invalid parameter')
            expected_desc = ('The "coord" parameter is invalid. '
                             'The value is not formatted correctly.')
            self.assertEqual(ex.description, expected_desc)

    def test_param_property(self):
        query_string = 'ant=4&bee=3&cat=2&dog=1'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        self.assertEqual(
            sorted(req.params.items()),
            [('ant', '4'), ('bee', '3'), ('cat', '2'), ('dog', '1')])

    def test_multiple_form_keys(self):
        query_string = 'ant=1&ant=2&bee=3&cat=6&cat=5&cat=4'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        # By definition, we cannot guarantee which of the multiple keys will
        # be returned by .get_param().
        self.assertIn(req.get_param('ant'), ('1', '2'))
        # There is only one 'bee' key so it remains a scalar.
        self.assertEqual(req.get_param('bee'), '3')
        # There are three 'cat' keys; order is preserved.
        self.assertIn(req.get_param('cat'), ('6', '5', '4'))

    def test_multiple_keys_as_bool(self):
        query_string = 'ant=true&ant=yes&ant=True'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_bool('ant'), True)

    def test_multiple_keys_as_int(self):
        query_string = 'ant=1&ant=2&ant=3'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertIn(req.get_param_as_int('ant'), (1, 2, 3))

    def test_multiple_form_keys_as_list(self):
        query_string = 'ant=1&ant=2&bee=3&cat=6&cat=5&cat=4'
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        # There are two 'ant' keys.
        self.assertEqual(req.get_param_as_list('ant'), ['1', '2'])
        # There is only one 'bee' key..
        self.assertEqual(req.get_param_as_list('bee'), ['3'])
        # There are three 'cat' keys; order is preserved.
        self.assertEqual(req.get_param_as_list('cat'), ['6', '5', '4'])

    def test_get_date_valid(self):
        date_value = '2015-04-20'
        query_string = 'thedate={0}'.format(date_value)
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_date('thedate'),
                         date(2015, 4, 20))

    def test_get_date_missing_param(self):
        query_string = 'notthedate=2015-04-20'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_date('thedate'),
                         None)

    def test_get_date_valid_with_format(self):
        date_value = '20150420'
        query_string = 'thedate={0}'.format(date_value)
        format_string = '%Y%m%d'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_date('thedate',
                         format_string=format_string),
                         date(2015, 4, 20))

    def test_get_date_store(self):
        date_value = '2015-04-20'
        query_string = 'thedate={0}'.format(date_value)
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        store = {}
        req.get_param_as_date('thedate', store=store)
        self.assertNotEqual(len(store), 0)

    def test_get_date_invalid(self):
        date_value = 'notarealvalue'
        query_string = 'thedate={0}'.format(date_value)
        format_string = '%Y%m%d'
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertRaises(HTTPInvalidParam, req.get_param_as_date,
                          'thedate', format_string=format_string)

    def test_get_dict_valid(self):
        payload_dict = {'foo': 'bar'}
        query_string = 'payload={0}'.format(json.dumps(payload_dict))
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_dict('payload'),
                         payload_dict)

    def test_get_dict_missing_param(self):
        payload_dict = {'foo': 'bar'}
        query_string = 'notthepayload={0}'.format(json.dumps(payload_dict))
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertEqual(req.get_param_as_dict('payload'),
                         None)

    def test_get_dict_store(self):
        payload_dict = {'foo': 'bar'}
        query_string = 'payload={0}'.format(json.dumps(payload_dict))
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        store = {}
        req.get_param_as_dict('payload', store=store)
        self.assertNotEqual(len(store), 0)

    def test_get_dict_invalid(self):
        payload_dict = 'foobar'
        query_string = 'payload={0}'.format(payload_dict)
        self.simulate_request('/', query_string=query_string)
        req = self.resource.captured_req
        self.assertRaises(HTTPInvalidParam, req.get_param_as_dict,
                          'payload')


@ddt.ddt
class PostQueryParams(_TestQueryParams):
    def before(self):
        super(PostQueryParams, self).before()
        self.api.req_options.auto_parse_form_urlencoded = True

    def simulate_request(self, path, query_string, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if 'method' not in kwargs:
            kwargs['method'] = 'POST'

        super(PostQueryParams, self).simulate_request(
            path,
            body=query_string,
            **kwargs
        )

    @ddt.data('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS')
    def test_http_methods_body_expected(self, http_method):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string,
                              method=http_method)

        req = self.resource.captured_req
        self.assertEqual(req.get_param('marker'), 'deadbeef')
        self.assertEqual(req.get_param('limit'), '25')

    @ddt.data('GET', 'HEAD')
    def test_http_methods_body_not_expected(self, http_method):
        query_string = 'marker=deadbeef&limit=25'
        self.simulate_request('/', query_string=query_string,
                              method=http_method)

        req = self.resource.captured_req
        self.assertEqual(req.get_param('marker'), None)
        self.assertEqual(req.get_param('limit'), None)

    def test_non_ascii(self):
        value = u'\u8c46\u74e3'
        query_string = b'q=' + value.encode('utf-8')
        self.simulate_request('/', query_string=query_string)

        req = self.resource.captured_req
        self.assertIs(req.get_param('q'), None)

    def test_empty_body(self):
        self.simulate_request('/', query_string=None)

        req = self.resource.captured_req
        self.assertIs(req.get_param('q'), None)

    def test_empty_body_no_content_length(self):
        self.simulate_request('/', query_string=None)

        req = self.resource.captured_req
        self.assertIs(req.get_param('q'), None)

    def test_explicitly_disable_auto_parse(self):
        self.api.req_options.auto_parse_form_urlencoded = False
        self.simulate_request('/', query_string='q=42')

        req = self.resource.captured_req
        self.assertIs(req.get_param('q'), None)


class GetQueryParams(_TestQueryParams):
    def simulate_request(self, path, query_string, **kwargs):
        super(GetQueryParams, self).simulate_request(
            path, query_string=query_string, **kwargs)


class PostQueryParamsDefaultBehavior(testing.TestBase):
    def test_dont_auto_parse_by_default(self):
        self.resource = testing.SimpleTestResource()
        self.api.add_route('/', self.resource)

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.simulate_request('/', body='q=42', headers=headers)

        req = self.resource.captured_req
        self.assertIs(req.get_param('q'), None)
