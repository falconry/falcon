from datetime import date, datetime
import json
from uuid import UUID

import pytest

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


@pytest.fixture
def resource():
    return Resource()


@pytest.fixture
def client():
    app = falcon.API()
    app.req_options.auto_parse_form_urlencoded = True
    return testing.TestClient(app)


def simulate_request_get_query_params(client, path, query_string, **kwargs):
    return client.simulate_request(path=path, query_string=query_string, **kwargs)


def simulate_request_post_query_params(client, path, query_string, **kwargs):
    headers = kwargs.setdefault('headers', {})
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if 'method' not in kwargs:
        kwargs['method'] = 'POST'
    return client.simulate_request(path=path, body=query_string, **kwargs)


@pytest.fixture(
    scope='session',
    params=[
        simulate_request_get_query_params,
        simulate_request_post_query_params,
    ],
)
def simulate_request(request):
    return request.param


class TestQueryParams(object):
    def test_none(self, simulate_request, client, resource):
        query_string = ''
        client.app.add_route('/', resource)  # TODO: DRY up this setup logic
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        store = {}
        assert req.get_param('marker') is None
        assert req.get_param('limit', store) is None
        assert 'limit' not in store
        assert req.get_param_as_int('limit') is None
        assert req.get_param_as_float('limit') is None
        assert req.get_param_as_bool('limit') is None
        assert req.get_param_as_list('limit') is None

    def test_default(self, simulate_request, client, resource):
        default = 'foobar'
        query_string = ''
        client.app.add_route('/', resource)  # TODO: DRY up this setup logic
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        store = {}
        assert req.get_param('marker', default=default) == 'foobar'
        assert req.get_param('limit', store, default=default) == 'foobar'
        assert 'limit' not in store
        assert req.get_param_as_int('limit', default=default) == 'foobar'
        assert req.get_param_as_float('limit', default=default) == 'foobar'
        assert req.get_param_as_bool('limit', default=default) == 'foobar'
        assert req.get_param_as_list('limit', default=default) == 'foobar'

    def test_blank(self, simulate_request, client, resource):
        query_string = 'marker='
        client.app.add_route('/', resource)
        client.app.req_options.keep_blank_qs_values = False
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        assert req.get_param('marker') is None

        store = {}
        assert req.get_param('marker', store=store) is None
        assert 'marker' not in store

    def test_simple(self, simulate_request, client, resource):
        query_string = 'marker=deadbeef&limit=25'
        client.app.add_route('/', resource)
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        store = {}
        assert req.get_param('marker', store=store) or 'nada' == 'deadbeef'
        assert req.get_param('limit', store=store) or '0' == '25'

        assert store['marker'] == 'deadbeef'
        assert store['limit'] == '25'

    def test_percent_encoded(self, simulate_request, client, resource):
        query_string = 'id=23,42&q=%e8%b1%86+%e7%93%a3'
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_qs_csv = True
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        assert req.get_param('id') in [u'23', u'42']

        assert req.get_param_as_list('id', int) == [23, 42]
        assert req.get_param('q') == u'\u8c46 \u74e3'

    def test_option_auto_parse_qs_csv_simple_false(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_qs_csv = False

        query_string = 'id=23,42,,&id=2'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        assert req.params['id'] == [u'23,42,,', u'2']
        assert req.get_param('id') in [u'23,42,,', u'2']
        assert req.get_param_as_list('id') == [u'23,42,,', u'2']

    def test_option_auto_parse_qs_csv_simple_true(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_qs_csv = True
        client.app.req_options.keep_blank_qs_values = False

        query_string = 'id=23,42,,&id=2'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        assert req.params['id'] == [u'23', u'42', u'2']
        assert req.get_param('id') in [u'23', u'42', u'2']
        assert req.get_param_as_list('id', int) == [23, 42, 2]

    def test_option_auto_parse_qs_csv_complex_false(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_qs_csv = False
        client.app.req_options.keep_blank_qs_values = False

        encoded_json = '%7B%22msg%22:%22Testing%201,2,3...%22,%22code%22:857%7D'
        decoded_json = '{"msg":"Testing 1,2,3...","code":857}'

        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing=' + encoded_json)

        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        assert req.get_param('colors') in 'red,green,blue'
        assert req.get_param_as_list('colors') == [u'red,green,blue']

        assert req.get_param_as_list('limit') == ['1']

        assert req.get_param_as_list('empty1') is None
        assert req.get_param_as_list('empty2') == [u',']
        assert req.get_param_as_list('empty3') == [u',,']

        assert req.get_param_as_list('list-ish1') == [u'f,,x']
        assert req.get_param_as_list('list-ish2') == [u',0']
        assert req.get_param_as_list('list-ish3') == [u'a,,,b']

        assert req.get_param('thing') == decoded_json

    def test_default_auto_parse_csv_behaviour(self, simulate_request, client, resource):
        client.app.add_route('/', resource=resource)
        query_string = 'id=1,2,,&id=3'

        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        assert req.get_param('id') == '3'
        assert req.get_param_as_list('id') == ['1,2,,', '3']

    def test_bad_percentage(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'x=%%20%+%&y=peregrine&z=%a%z%zz%1%20e'
        response = simulate_request(client=client, path='/', query_string=query_string)
        assert response.status == falcon.HTTP_200

        req = resource.captured_req
        assert req.get_param('x') == '% % %'
        assert req.get_param('y') == 'peregrine'
        assert req.get_param('z') == '%a%z%zz%1 e'

    def test_allowed_names(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.keep_blank_qs_values = False
        query_string = ('p=0&p1=23&2p=foo&some-thing=that&blank=&'
                        'some_thing=x&-bogus=foo&more.things=blah&'
                        '_thing=42&_charset_=utf-8')
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        assert req.get_param('p') == '0'
        assert req.get_param('p1') == '23'
        assert req.get_param('2p') == 'foo'
        assert req.get_param('some-thing') == 'that'
        assert req.get_param('blank') is None
        assert req.get_param('some_thing') == 'x'
        assert req.get_param('-bogus') == 'foo'
        assert req.get_param('more.things') == 'blah'
        assert req.get_param('_thing') == '42'
        assert req.get_param('_charset_') == 'utf-8'

    @pytest.mark.parametrize('method_name', [
        'get_param',
        'get_param_as_int',
        'get_param_as_float',
        'get_param_as_uuid',
        'get_param_as_bool',
        'get_param_as_list',
    ])
    def test_required(self, simulate_request, client, resource, method_name):
        client.app.add_route('/', resource)
        query_string = ''
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        try:
            getattr(req, method_name)('marker', required=True)
            pytest.fail('falcon.HTTPMissingParam not raised')
        except falcon.HTTPMissingParam as ex:
            assert isinstance(ex, falcon.HTTPBadRequest)
            assert ex.title == 'Missing parameter'
            expected_desc = 'The "marker" parameter is required.'
            assert ex.description == expected_desc

    def test_int(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'marker=deadbeef&limit=25'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        try:
            req.get_param_as_int('marker')
        except Exception as ex:
            assert isinstance(ex, falcon.HTTPBadRequest)
            assert isinstance(ex, falcon.HTTPInvalidParam)
            assert ex.title == 'Invalid parameter'
            expected_desc = ('The "marker" parameter is invalid. '
                             'The value must be an integer.')
            assert ex.description == expected_desc

        assert req.get_param_as_int('limit') == 25

        store = {}
        assert req.get_param_as_int('limit', store=store) == 25
        assert store['limit'] == 25

        assert req.get_param_as_int('limit', min_value=1, max_value=50) == 25

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('limit', min_value=0, max_value=10)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('limit', min_value=0, max_value=24)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('limit', min_value=30, max_value=24)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('limit', min_value=30, max_value=50)

        assert req.get_param_as_int('limit', min_value=1) == 25

        assert req.get_param_as_int('limit', max_value=50) == 25

        assert req.get_param_as_int('limit', max_value=25) == 25

        assert req.get_param_as_int('limit', max_value=26) == 25

        assert req.get_param_as_int('limit', min_value=25) == 25

        assert req.get_param_as_int('limit', min_value=24) == 25

        assert req.get_param_as_int('limit', min_value=-24) == 25

    def test_int_neg(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'marker=deadbeef&pos=-7'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        assert req.get_param_as_int('pos') == -7

        assert req.get_param_as_int('pos', min_value=-10, max_value=10) == -7

        assert req.get_param_as_int('pos', max_value=10) == -7

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('pos', min_value=-6, max_value=0)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('pos', min_value=-6)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('pos', min_value=0, max_value=10)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_int('pos', min_value=0, max_value=10)

    def test_float(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'marker=deadbeef&limit=25.1'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        try:
            req.get_param_as_float('marker')
        except Exception as ex:
            assert isinstance(ex, falcon.HTTPBadRequest)
            assert isinstance(ex, falcon.HTTPInvalidParam)
            assert ex.title == 'Invalid parameter'
            expected_desc = ('The "marker" parameter is invalid. '
                             'The value must be a float.')
            assert ex.description == expected_desc

        assert req.get_param_as_float('limit') == 25.1

        store = {}
        assert req.get_param_as_float('limit', store=store) == 25.1
        assert store['limit'] == 25.1

        assert req.get_param_as_float('limit', min_value=1, max_value=50) == 25.1

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('limit', min_value=0, max_value=10)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('limit', min_value=0, max_value=24)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('limit', min_value=30, max_value=24)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('limit', min_value=30, max_value=50)

        assert req.get_param_as_float('limit', min_value=1) == 25.1

        assert req.get_param_as_float('limit', max_value=50) == 25.1

        assert req.get_param_as_float('limit', max_value=25.1) == 25.1

        assert req.get_param_as_float('limit', max_value=26) == 25.1

        assert req.get_param_as_float('limit', min_value=25) == 25.1

        assert req.get_param_as_float('limit', min_value=24) == 25.1

        assert req.get_param_as_float('limit', min_value=-24) == 25.1

    def test_float_neg(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'marker=deadbeef&pos=-7.1'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        assert req.get_param_as_float('pos') == -7.1

        assert req.get_param_as_float('pos', min_value=-10, max_value=10) == -7.1

        assert req.get_param_as_float('pos', max_value=10) == -7.1

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('pos', min_value=-6, max_value=0)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('pos', min_value=-6)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('pos', min_value=0, max_value=10)

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_float('pos', min_value=0, max_value=10)

    def test_uuid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = ('marker1=8d76b7b3-d0dd-46ca-ad6e-3989dcd66959&'
                        'marker2=64be949b-3433-4d36-a4a8-9f19d352fee8&'
                        'marker2=8D76B7B3-d0dd-46ca-ad6e-3989DCD66959&'
                        'short=4be949b-3433-4d36-a4a8-9f19d352fee8')
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        expected_uuid = UUID('8d76b7b3-d0dd-46ca-ad6e-3989dcd66959')
        assert req.get_param_as_uuid('marker1') == expected_uuid
        assert req.get_param_as_uuid('marker2') == expected_uuid
        assert req.get_param_as_uuid('marker3') is None
        assert req.get_param_as_uuid('marker3', required=False) is None

        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_uuid('short')

        store = {}
        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_uuid('marker3', required=True, store=store)

        assert not store
        assert req.get_param_as_uuid('marker1', store=store)
        assert store['marker1'] == expected_uuid

    def test_boolean(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.keep_blank_qs_values = False
        query_string = ('echo=true&doit=false&bogus=bar&bogus2=foo&'
                        't1=True&f1=False&t2=yes&f2=no&blank&one=1&zero=0&'
                        'checkbox1=on&checkbox2=off')
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        with pytest.raises(falcon.HTTPBadRequest):
            req.get_param_as_bool('bogus')

        try:
            req.get_param_as_bool('bogus2')
        except Exception as ex:
            assert isinstance(ex, falcon.HTTPInvalidParam)
            assert ex.title == 'Invalid parameter'
            expected_desc = ('The "bogus2" parameter is invalid. '
                             'The value of the parameter must be "true" '
                             'or "false".')
            assert ex.description == expected_desc

        assert req.get_param_as_bool('echo') is True
        assert req.get_param_as_bool('doit') is False

        assert req.get_param_as_bool('t1') is True
        assert req.get_param_as_bool('t2') is True
        assert req.get_param_as_bool('f1') is False
        assert req.get_param_as_bool('f2') is False
        assert req.get_param_as_bool('one') is True
        assert req.get_param_as_bool('zero') is False
        assert req.get_param('blank') is None

        assert req.get_param_as_bool('checkbox1') is True
        assert req.get_param_as_bool('checkbox2') is False

        store = {}
        assert req.get_param_as_bool('echo', store=store) is True
        assert store['echo'] is True

    def test_boolean_blank(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        simulate_request(client=client, path='/', query_string='blank&blank2=')

        req = resource.captured_req
        assert req.get_param('blank') == ''
        assert req.get_param('blank2') == ''

        for param_name in ('blank', 'blank2'):
            assert req.get_param_as_bool(param_name) is True
            assert req.get_param_as_bool(param_name, blank_as_true=True) is True
            assert req.get_param_as_bool(param_name, blank_as_true=False) is False

        assert req.get_param_as_bool('nichts') is None
        assert req.get_param_as_bool('nichts', default=None) is None
        assert req.get_param_as_bool('nichts', default=False) is False
        assert req.get_param_as_bool('nichts', default=True) is True

    def test_list_type(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_qs_csv = True
        client.app.req_options.keep_blank_qs_values = False
        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing_one=1,,3'
                        '&thing_two=1&thing_two=&thing_two=3')
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        assert req.get_param('colors') in ('red', 'green', 'blue')

        assert req.get_param_as_list('colors') == ['red', 'green', 'blue']
        assert req.get_param_as_list('limit') == ['1']
        assert req.get_param_as_list('marker') is None

        assert req.get_param_as_list('empty1') is None
        assert req.get_param_as_list('empty2') == []
        assert req.get_param_as_list('empty3') == []

        assert req.get_param_as_list('list-ish1') == ['f', 'x']

        # Ensure that '0' doesn't get translated to None
        assert req.get_param_as_list('list-ish2') == ['0']

        # Ensure that '0' doesn't get translated to None
        assert req.get_param_as_list('list-ish3') == ['a', 'b']

        # Ensure consistency between list conventions
        assert req.get_param_as_list('thing_one') == ['1', '3']
        assert (
            req.get_param_as_list('thing_one') ==
            req.get_param_as_list('thing_two')
        )

        store = {}
        assert req.get_param_as_list('limit', store=store) == ['1']
        assert store['limit'] == ['1']

    def test_list_type_blank(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = ('colors=red,green,blue&limit=1'
                        '&list-ish1=f,,x&list-ish2=,0&list-ish3=a,,,b'
                        '&empty1=&empty2=,&empty3=,,'
                        '&thing_one=1,,3'
                        '&thing_two=1&thing_two=&thing_two=3'
                        '&empty4=&empty4&empty4='
                        '&empty5&empty5&empty5')
        client.app.req_options.keep_blank_qs_values = True
        client.app.req_options.auto_parse_qs_csv = True
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        assert req.get_param('colors') in ('red', 'green', 'blue')

        assert req.get_param_as_list('colors') == ['red', 'green', 'blue']
        assert req.get_param_as_list('limit') == ['1']
        assert req.get_param_as_list('marker') is None

        assert req.get_param_as_list('empty1') == ['']
        assert req.get_param_as_list('empty2') == ['', '']
        assert req.get_param_as_list('empty3') == ['', '', '']

        assert req.get_param_as_list('list-ish1') == ['f', '', 'x']

        # Ensure that '0' doesn't get translated to None
        assert req.get_param_as_list('list-ish2') == ['', '0']

        # Ensure that '0' doesn't get translated to None
        assert req.get_param_as_list('list-ish3') == ['a', '', '', 'b']

        # Ensure consistency between list conventions
        assert req.get_param_as_list('thing_one') == ['1', '', '3']
        assert req.get_param_as_list('thing_one') == req.get_param_as_list('thing_two')

        store = {}
        assert req.get_param_as_list('limit', store=store) == ['1']
        assert store['limit'] == ['1']

        # Test empty elements
        assert req.get_param_as_list('empty4') == ['', '', '']
        assert req.get_param_as_list('empty5') == ['', '', '']
        assert req.get_param_as_list('empty4') == req.get_param_as_list('empty5')

    def test_list_transformer(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_qs_csv = True
        client.app.req_options.keep_blank_qs_values = False
        query_string = 'coord=1.4,13,15.1&limit=100&things=4,,1'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req

        # NOTE(kgriffs): For lists, get_param will return one of the
        # elements, but which one it will choose is undefined.
        assert req.get_param('coord') in ('1.4', '13', '15.1')

        expected = [1.4, 13.0, 15.1]
        actual = req.get_param_as_list('coord', transform=float)
        assert actual == expected

        expected = ['4', '1']
        actual = req.get_param_as_list('things', transform=str)
        assert actual == expected

        expected = [4, 1]
        actual = req.get_param_as_list('things', transform=int)
        assert actual == expected

        try:
            req.get_param_as_list('coord', transform=int)
        except Exception as ex:
            assert isinstance(ex, falcon.HTTPInvalidParam)
            assert ex.title == 'Invalid parameter'
            expected_desc = ('The "coord" parameter is invalid. '
                             'The value is not formatted correctly.')
            assert ex.description == expected_desc

    def test_param_property(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=4&bee=3&cat=2&dog=1'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        assert (
            sorted(req.params.items()) ==
            [('ant', '4'), ('bee', '3'), ('cat', '2'), ('dog', '1')]
        )

    def test_multiple_form_keys(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=1&ant=2&bee=3&cat=6&cat=5&cat=4'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        # By definition, we cannot guarantee which of the multiple keys will
        # be returned by .get_param().
        assert req.get_param('ant') in ('1', '2')
        # There is only one 'bee' key so it remains a scalar.
        assert req.get_param('bee') == '3'
        # There are three 'cat' keys; order is preserved.
        assert req.get_param('cat') in ('6', '5', '4')

    def test_multiple_keys_as_bool(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=true&ant=yes&ant=True'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_bool('ant') is True

    def test_multiple_keys_as_int(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=1&ant=2&ant=3'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_int('ant') in (1, 2, 3)

    def test_multiple_keys_as_float(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=1.1&ant=2.2&ant=3.3'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_float('ant') in (1.1, 2.2, 3.3)

    def test_multiple_form_keys_as_list(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=1&ant=2&bee=3&cat=6&cat=5&cat=4'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        # There are two 'ant' keys.
        assert req.get_param_as_list('ant') == ['1', '2']
        # There is only one 'bee' key..
        assert req.get_param_as_list('bee') == ['3']
        # There are three 'cat' keys; order is preserved.
        assert req.get_param_as_list('cat') == ['6', '5', '4']

    def test_get_date_valid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = '2015-04-20'
        query_string = 'thedate={}'.format(date_value)
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_date('thedate') == date(2015, 4, 20)

    def test_get_date_missing_param(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'notthedate=2015-04-20'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_date('thedate') is None

    def test_get_date_valid_with_format(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = '20150420'
        query_string = 'thedate={}'.format(date_value)
        format_string = '%Y%m%d'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_date('thedate', format_string=format_string) == date(2015, 4, 20)

    def test_get_date_store(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = '2015-04-20'
        query_string = 'thedate={}'.format(date_value)
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        store = {}
        req.get_param_as_date('thedate', store=store)
        assert len(store) != 0

    def test_get_date_invalid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = 'notarealvalue'
        query_string = 'thedate={}'.format(date_value)
        format_string = '%Y%m%d'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        with pytest.raises(HTTPInvalidParam):
            req.get_param_as_date('thedate', format_string=format_string)

    def test_get_datetime_valid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = '2015-04-20T10:10:10Z'
        query_string = 'thedate={}'.format(date_value)
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_datetime('thedate') == datetime(2015, 4, 20, 10, 10, 10)

    def test_get_datetime_missing_param(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'notthedate=2015-04-20T10:10:10Z'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_datetime('thedate') is None

    def test_get_datetime_valid_with_format(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = '20150420 10:10:10'
        query_string = 'thedate={}'.format(date_value)
        format_string = '%Y%m%d %H:%M:%S'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_datetime(
            'thedate', format_string=format_string) == datetime(2015, 4, 20, 10, 10, 10)

    def test_get_datetime_store(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        datetime_value = '2015-04-20T10:10:10Z'
        query_string = 'thedate={}'.format(datetime_value)
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        store = {}
        req.get_param_as_datetime('thedate', store=store)
        assert len(store) != 0
        assert store.get('thedate') == datetime(2015, 4, 20, 10, 10, 10)

    def test_get_datetime_invalid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        date_value = 'notarealvalue'
        query_string = 'thedate={}'.format(date_value)
        format_string = '%Y%m%dT%H:%M:%S'
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        with pytest.raises(HTTPInvalidParam):
            req.get_param_as_datetime('thedate', format_string=format_string)

    def test_get_dict_valid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        payload_dict = {'foo': 'bar'}
        query_string = 'payload={}'.format(json.dumps(payload_dict))
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_json('payload') == payload_dict

    def test_get_dict_missing_param(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        payload_dict = {'foo': 'bar'}
        query_string = 'notthepayload={}'.format(json.dumps(payload_dict))
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        assert req.get_param_as_json('payload') is None

    def test_get_dict_store(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        payload_dict = {'foo': 'bar'}
        query_string = 'payload={}'.format(json.dumps(payload_dict))
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        store = {}
        req.get_param_as_json('payload', store=store)
        assert len(store) != 0

    def test_get_dict_invalid(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        payload_dict = 'foobar'
        query_string = 'payload={}'.format(payload_dict)
        simulate_request(client=client, path='/', query_string=query_string)
        req = resource.captured_req
        with pytest.raises(HTTPInvalidParam):
            req.get_param_as_json('payload')

    def test_has_param(self, simulate_request, client, resource):
        client.app.add_route('/', resource)
        query_string = 'ant=1'
        simulate_request(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        # There is a 'ant' key.
        assert req.has_param('ant')
        # There is not a 'bee' key..
        assert not req.has_param('bee')
        # There is not a None key
        assert not req.has_param(None)


class TestPostQueryParams(object):
    @pytest.mark.parametrize('http_method', ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'))
    def test_http_methods_body_expected(self, client, resource, http_method):
        client.app.add_route('/', resource)
        query_string = 'marker=deadbeef&limit=25'
        simulate_request_post_query_params(client=client, path='/', query_string=query_string,
                                           method=http_method)

        req = resource.captured_req
        assert req.get_param('marker') == 'deadbeef'
        assert req.get_param('limit') == '25'

    @pytest.mark.parametrize('http_method', ('GET', 'HEAD'))
    def test_http_methods_body_not_expected(self, client, resource, http_method):
        client.app.add_route('/', resource)
        query_string = 'marker=deadbeef&limit=25'
        simulate_request_post_query_params(client=client, path='/', query_string=query_string,
                                           method=http_method)

        req = resource.captured_req
        assert req.get_param('marker') is None
        assert req.get_param('limit') is None

    def test_non_ascii(self, client, resource):
        client.app.add_route('/', resource)
        value = u'\u8c46\u74e3'
        query_string = b'q=' + value.encode('utf-8')
        simulate_request_post_query_params(client=client, path='/', query_string=query_string)

        req = resource.captured_req
        assert req.get_param('q') is None

    def test_empty_body(self, client, resource):
        client.app.add_route('/', resource)
        simulate_request_post_query_params(client=client, path='/', query_string=None)

        req = resource.captured_req
        assert req.get_param('q') is None

    def test_empty_body_no_content_length(self, client, resource):
        client.app.add_route('/', resource)
        simulate_request_post_query_params(client=client, path='/', query_string=None)

        req = resource.captured_req
        assert req.get_param('q') is None

    def test_explicitly_disable_auto_parse(self, client, resource):
        client.app.add_route('/', resource)
        client.app.req_options.auto_parse_form_urlencoded = False
        simulate_request_post_query_params(client=client, path='/', query_string='q=42')

        req = resource.captured_req
        assert req.get_param('q') is None


class TestPostQueryParamsDefaultBehavior(object):
    def test_dont_auto_parse_by_default(self):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        client = testing.TestClient(app)

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        client.simulate_request(path='/', body='q=42', headers=headers)

        req = resource.captured_req
        assert req.get_param('q') is None
