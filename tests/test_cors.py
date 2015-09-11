import re
import uuid

import mock
from nose.tools import raises

import falcon
from falcon.cors import CORS
import falcon.testing as testing
from falcon.testing.resource import TestResource


class CORSResource(TestResource):
    def on_options(self, req, resp, **kwargs):
        self.req, self.resp, self.kwargs = req, resp, kwargs


class TestCors(testing.TestBase):
    def get_header(self, name):
        return self.resource.resp._headers.get(name.lower(), None)

    def get_rand_str(self):
        return str(uuid.uuid4())

    def simulate_cors_api(self, cors, route='/'):
        self.api = falcon.API(cors=cors)
        self.api.add_route(route, self.resource)

    @raises(ValueError)
    def test_api_cors_instance(self):
        not_a_cors = {}
        falcon.API(cors=not_a_cors)

    def test_api_insert_middleware(self):
        cors = CORS()

        class FakeMiddleware:
            def process_resource(self, req, resp, resource):
                pass

        fake_middleware = FakeMiddleware()
        api = falcon.API(middleware=[fake_middleware], cors=cors)
        print(api._middleware)
        self.assertEqual(len(api._middleware), 2)
        self.assertEqual(api._middleware[0][1].__self__.cors, cors)

    @raises(ValueError)
    def test_init_settings(self):
        CORS(not_a_real_setting=True)

    @raises(ValueError)
    def test_init_allowed_methods(self):
        CORS(allow_methods_list=['not_a_real_method'])

    def test_vary_origins_true(self):
        cors = CORS(allow_all_origins=True, allow_credentials_origins_list=['test.com'])
        self.assertTrue(cors.origins_vary)

    def test_vary_origins_false(self):
        cors = CORS()
        self.assertFalse(cors.origins_vary)

    def test_compile_keys(self):
        regex_string = '.*'
        compiled_regex = re.compile(regex_string)
        test_compile_dict = {'some_regex': regex_string}
        cors = CORS()
        cors._compile_keys(test_compile_dict, ['some_regex'])
        self.assertEqual(compiled_regex, test_compile_dict['some_regex'])

    def simulate_cors_request(self, cors, route='/', preflight=False,
                              preflight_method='PATCH', add_request_method=True, **kwargs):
        self.resource = CORSResource()
        if preflight:
            kwargs.setdefault('headers', [])
            if add_request_method:
                kwargs['headers'].append(('access-control-request-method', preflight_method))
            method = 'OPTIONS'
        else:
            method = kwargs.pop('method', 'GET')

        self.simulate_cors_api(cors, route)
        self.simulate_request(route, method=method, **kwargs)

    def test_cors_disabled(self):
        self.resource = mock.MagicMock()
        self.resource.cors_enabled = False
        cors = CORS()
        cors.process = mock.Mock()
        self.simulate_cors_api(cors, '/')
        self.simulate_request('/', method='POST')
        self.assertEquals(cors.process.call_count, 0)

    def simulate_all_origins(self, preflight=False):
        cors_config = CORS(allow_all_origins=True, allow_methods_list=['PATCH'])
        origin = self.get_rand_str()
        headers = [('origin', origin)]
        self.simulate_cors_request(cors_config, headers=headers, preflight=preflight)
        self.assertEqual(self.get_header('access-control-allow-origin'), '*')
        self.assertEqual(self.get_header('access-control-allow-credentials'), None)

    def test_all_origins(self):
        self.simulate_all_origins()
        self.simulate_all_origins(preflight=True)

    def test_all_origins_credentials(self, preflight=False):
        cors_config = CORS(allow_all_origins=True, allow_credentials_all_origins=True,
                           allow_all_methods=True)
        origin = self.get_rand_str()
        headers = [('origin', origin)]
        self.simulate_cors_request(cors_config, headers=headers, preflight=preflight)
        self.assertEqual(self.get_header('access-control-allow-origin'), origin)
        self.assertEqual(self.get_header('access-control-allow-credentials'), 'true')

    def test_vary_origins_called(self):
        cors = CORS(allow_all_origins=True, allow_credentials_origins_list=['test.com'])
        cors._set_vary_origin = mock.Mock()
        origin = self.get_rand_str()
        headers = [('origin', origin)]
        self.simulate_cors_request(cors, headers=headers, preflight=False)
        cors._set_vary_origin.assert_called_once_with(self.resource.resp)

    def test_no_origin_return(self):
        cors = CORS()
        cors._process_origin = mock.Mock()
        self.simulate_cors_request(cors, preflight=False)
        self.assertEqual(cors._process_origin.call_count, 0)

    def test_process_origin_return(self):
        cors = CORS(allow_origins_list=['test.com'])
        cors._process_origin = mock.Mock(return_value=False)
        cors._process_credentials = mock.Mock()
        headers = [('origin', 'rackspace.com')]
        self.simulate_cors_request(cors, headers=headers, preflight=False)
        self.assertEqual(cors._process_origin.call_count, 1)
        self.assertEqual(cors._process_credentials.call_count, 0)

    def test_no_requested_method(self):
        cors = CORS(allow_all_origins=True)
        cors._get_requested_headers = mock.Mock()
        cors._process_origin = mock.Mock(return_value=True)
        headers = [('origin', 'rackspace.com')]
        self.simulate_cors_request(cors, headers=headers,
                                   preflight=True, add_request_method=False)
        self.assertEqual(cors._process_origin.call_count, 1)
        self.assertEqual(cors._get_requested_headers.call_count, 0)

    def test_method_not_allowed(self):
        cors = CORS(allow_all_origins=True, allow_methods_list=['GET'])
        cors._get_requested_headers = mock.Mock(return_value=True)
        cors._process_allow_headers = mock.Mock()
        headers = [('origin', 'rackspace.com')]
        self.simulate_cors_request(cors, headers=headers,
                                   preflight=True, preflight_method='POST')
        self.assertEqual(cors._get_requested_headers.call_count, 1)
        self.assertEqual(cors._process_allow_headers.call_count, 0)

    def test_header_not_allowed(self):
        cors = CORS(allow_all_origins=True, allow_all_methods=True,
                    allow_headers_list=['test_header'])
        cors._process_methods = mock.Mock(return_value=True)
        cors._process_credentials = mock.Mock()
        headers = [
            ('origin', 'rackspace.com'),
            ('access-control-request-headers', 'not_allowed_header')
        ]
        self.simulate_cors_request(cors, headers=headers, preflight=True)
        self.assertEqual(cors._process_methods.call_count, 1)
        self.assertEqual(cors._process_credentials.call_count, 0)

    def test_process_credentials_called(self):
        cors = CORS(allow_all_origins=True, allow_all_methods=True, allow_all_headers=True)
        cors._process_methods = mock.Mock(return_value=True)
        cors._process_credentials = mock.Mock()
        headers = [('origin', 'rackspace.com')]
        self.simulate_cors_request(cors, headers=headers, preflight=True)
        # print(cors._process_methods.call_count)
        cors._process_credentials.assert_called_once_with(
            self.resource.req,
            self.resource.resp,
            'rackspace.com'
        )

    def test_process_origin_allow_all(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_all_origins=True)
        cors._set_allow_origin = mock.Mock()
        self.assertEqual(
            cors._process_origin(fake_req, fake_resp, 'rackspace.com'),
            True
        )
        cors._set_allow_origin.assert_called_once_with(fake_resp, '*')
        cors._set_allow_origin = mock.Mock()
        cors.supports_credentials = True
        self.assertEqual(
            cors._process_origin(fake_req, fake_resp, 'rackspace.com'),
            True
        )
        cors._set_allow_origin.assert_called_once_with(fake_resp, 'rackspace.com')

    def test_process_origin_allow_list(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_origins_list=['rackspace.com'])
        cors._set_allow_origin = mock.Mock()
        self.assertEqual(
            cors._process_origin(fake_req, fake_resp, 'rackspace.com'),
            True
        )
        cors._set_allow_origin.assert_called_once_with(fake_resp, 'rackspace.com')

    def test_process_origin_allow_regex(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_origins_regex='rack.*\.com')
        cors._set_allow_origin = mock.Mock()
        self.assertEqual(
            cors._process_origin(fake_req, fake_resp, 'rackspace.com'),
            True
        )
        cors._set_allow_origin.assert_called_once_with(fake_resp, 'rackspace.com')

    def test_process_origin_regex_none(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS()
        cors._set_allow_origin = mock.Mock()
        self.assertEqual(
            cors._process_origin(fake_req, fake_resp, 'rackspace.com'),
            False
        )
        self.assertEqual(cors._set_allow_origin.call_count, 0)

    def test_process_origin_deny(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(
            allow_origins_list=['rackspace.com'],
            allow_origins_regex='rack.*\.com'
        )
        cors._set_allow_origin = mock.Mock()
        self.assertEqual(
            cors._process_origin(fake_req, fake_resp, 'not_rackspace.com'),
            False
        )
        self.assertEqual(cors._set_allow_origin.call_count, 0)

    def test_process_allow_headers_all(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_all_headers=True)
        cors._set_allowed_headers = mock.Mock()
        self.assertEqual(
            cors._process_allow_headers(fake_req, fake_resp, ['test_header']),
            True
        )
        cors._set_allowed_headers.assert_called_once_with(fake_resp, ['test_header'])

    def test_process_allow_headers_list(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_headers_list=['test_header'])
        cors._set_allowed_headers = mock.Mock()
        self.assertEqual(
            cors._process_allow_headers(fake_req, fake_resp, ['test_header']),
            True
        )
        cors._set_allowed_headers.assert_called_once_with(fake_resp, ['test_header'])

    def test_process_allow_headers_regex(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_headers_regex='.*_header')
        cors._set_allowed_headers = mock.Mock()
        self.assertEqual(
            cors._process_allow_headers(fake_req, fake_resp, ['test_header']),
            True
        )
        cors._set_allowed_headers.assert_called_once_with(fake_resp, ['test_header'])

    def test_process_allow_headers_disallow(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_headers_list=['test_header'], allow_headers_regex='.*_header')
        cors._set_allowed_headers = mock.Mock()
        self.assertEqual(
            cors._process_allow_headers(
                fake_req, fake_resp, ['test_header', 'header_not_allowed']
            ),
            False
        )
        self.assertEqual(cors._set_allowed_headers.call_count, 0)

    def test_process_methods_not_requested(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        fake_resource = mock.MagicMock()
        cors = CORS(allow_all_methods=True)
        cors._get_requested_method = mock.Mock(return_value=None)
        cors._set_allowed_methods = mock.Mock()
        self.assertEqual(
            cors._process_methods(fake_req, fake_resp, fake_resource),
            False
        )
        self.assertEqual(cors._set_allowed_methods.call_count, 0)
        cors._get_requested_method.assert_called_once_with(fake_req)

    def test_process_methods_allow_all_allowed(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        fake_resource = mock.MagicMock()
        cors = CORS(allow_all_methods=True)
        cors._get_requested_method = mock.Mock(return_value='GET')
        cors._get_resource_methods = mock.Mock(return_value=['GET', 'POST'])
        cors._set_allowed_methods = mock.Mock()
        self.assertEqual(
            cors._process_methods(fake_req, fake_resp, fake_resource),
            True
        )
        cors._set_allowed_methods.assert_called_once_with(fake_resp, ['GET', 'POST'])

    def test_process_methods_resource(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        fake_resource = mock.MagicMock()
        cors = CORS(allow_all_methods=True)
        cors._get_requested_method = mock.Mock(return_value='GET')
        cors._get_resource_methods = mock.Mock(return_value=['POST'])
        cors._set_allowed_methods = mock.Mock()
        self.assertEqual(
            cors._process_methods(fake_req, fake_resp, fake_resource),
            False
        )
        cors._set_allowed_methods.assert_called_once_with(fake_resp, ['POST'])

    def test_process_methods_allow_list(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        fake_resource = mock.MagicMock()
        cors = CORS(allow_methods_list=['GET', 'PUT', 'DELETE'])
        cors._set_allowed_methods = mock.Mock()
        cors._get_requested_method = mock.Mock(return_value='GET')
        cors._get_resource_methods = mock.Mock(return_value=['GET', 'POST', 'PUT'])
        self.assertEqual(
            cors._process_methods(fake_req, fake_resp, fake_resource),
            True
        )
        cors._set_allowed_methods.assert_called_once_with(fake_resp, ['GET', 'PUT'])

    def test_process_methods_notfound(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        fake_resource = mock.MagicMock()
        cors = CORS(allow_methods_list=['GET', 'POST', 'PUT', 'DELETE'])
        cors._set_allowed_methods = mock.Mock()
        cors._get_requested_method = mock.Mock(return_value='POST')
        cors._get_resource_methods = mock.Mock(return_value=['GET', 'PUT'])
        self.assertEqual(
            cors._process_methods(fake_req, fake_resp, fake_resource),
            False
        )
        cors._set_allowed_methods.assert_called_once_with(fake_resp, ['GET', 'PUT'])

    def test_process_credentials_all_origins(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_credentials_all_origins=True)
        cors._set_allow_credentials = mock.Mock()
        self.assertEqual(
            cors._process_credentials(fake_req, fake_resp, 'rackspace.com'),
            True
        )
        cors._set_allow_credentials.assert_called_once_with(fake_resp)

    def test_process_credentials_origins_list(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(allow_credentials_origins_list=['rackspace.com'])
        cors._set_allow_credentials = mock.Mock()
        self.assertEqual(
            cors._process_credentials(fake_req, fake_resp, 'rackspace.com'),
            True
        )
        cors._set_allow_credentials.assert_called_once_with(fake_resp)

    def test_process_credentials_regex(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(
            allow_credentials_origins_regex='.*\.rackspace\..*'
        )
        cors._set_allow_credentials = mock.Mock()
        self.assertEqual(
            cors._process_credentials(fake_req, fake_resp, 'www.rackspace.com'),
            True
        )
        cors._set_allow_credentials.assert_called_once_with(fake_resp)

    def test_process_credentials_disallow(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(
            allow_credentials_origins_list=['not_rackspace'],
            allow_credentials_origins_regex='.*\.rackspace\..*'
        )
        cors._set_allow_credentials = mock.Mock()
        self.assertEqual(
            cors._process_credentials(fake_req, fake_resp, 'some_other_domain.lan'),
            False
        )
        self.assertEqual(cors._set_allow_credentials.call_count, 0)

    def test_process_expose_headers(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(expose_headers_list=['test_header'])
        cors._process_expose_headers(fake_req, fake_resp)
        fake_resp.append_header.assert_called_once_with(
            'access-control-expose-headers', 'test_header'
        )

    def test_process_max_age(self):
        fake_req = mock.MagicMock()
        fake_resp = mock.MagicMock()
        cors = CORS(max_age=5)
        cors._process_max_age(fake_req, fake_resp)
        fake_resp.set_header.assert_called_once_with('access-control-max-age', 5)

    def test_set_allowed_headers(self):
        fake_resp = mock.MagicMock()
        allowed_header_list = ['header1']
        cors = CORS()
        cors._set_allowed_headers(fake_resp, allowed_header_list)
        fake_resp.append_header.assert_called_once_with('access-control-allow-headers', 'header1')

    def test_set_allowed_methods(self):
        fake_resp = mock.MagicMock()
        allowed_method_list = ['GET']
        cors = CORS()
        cors._set_allowed_methods(fake_resp, allowed_method_list)
        fake_resp.append_header.assert_called_once_with('access-control-allow-methods', 'GET')

    def test_set_very_origin(self):
        fake_resp = mock.MagicMock()
        cors = CORS()
        cors._set_vary_origin(fake_resp)
        fake_resp.append_header.assert_called_once_with('vary', 'origin')
