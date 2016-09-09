from datetime import datetime
import json

import falcon
import falcon.testing as testing

_EXPECTED_BODY = {u'status': u'ok'}

context = {'executed_methods': []}


class CaptureResponseMiddleware(object):

    def process_response(self, req, resp, resource, req_succeeded):
        self.req = req
        self.resp = resp
        self.resource = resource
        self.req_succeeded = req_succeeded


class RequestTimeMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['start_time'] = datetime.utcnow()

    def process_resource(self, req, resp, resource, params):
        global context
        context['mid_time'] = datetime.utcnow()

    def process_response(self, req, resp, resource, req_succeeded):
        global context
        context['end_time'] = datetime.utcnow()
        context['req_succeeded'] = req_succeeded


class TransactionIdMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['transaction_id'] = 'unique-req-id'

    def process_response(self, req, resp, resource):
        pass


class ExecutedFirstMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['executed_methods'].append(
            '{0}.{1}'.format(self.__class__.__name__, 'process_request'))

    def process_resource(self, req, resp, resource, params):
        global context
        context['executed_methods'].append(
            '{0}.{1}'.format(self.__class__.__name__, 'process_resource'))

    # NOTE(kgriffs): This also tests that the framework can continue to
    # call process_response() methods that do not have a 'req_succeeded'
    # arg.
    def process_response(self, req, resp, resource):
        global context
        context['executed_methods'].append(
            '{0}.{1}'.format(self.__class__.__name__, 'process_response'))

        context['req'] = req
        context['resp'] = resp
        context['resource'] = resource


class ExecutedLastMiddleware(ExecutedFirstMiddleware):
    pass


class RemoveBasePathMiddleware(object):

    def process_request(self, req, resp):
        req.path = req.path.replace('/base_path', '', 1)


class AccessParamsMiddleware(object):

    def process_resource(self, req, resp, resource, params):
        global context
        params['added'] = True
        context['params'] = params


class MiddlewareClassResource(object):

    def on_get(self, req, resp, **kwargs):
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(_EXPECTED_BODY)

    def on_post(self, req, resp):
        raise falcon.HTTPForbidden(falcon.HTTP_403, 'Setec Astronomy')


class TestMiddleware(testing.TestBase):

    def setUp(self):
        # Clear context
        global context
        context = {'executed_methods': []}
        testing.TestBase.setUp(self)

    # TODO(kgriffs): Consider adding this to TestBase
    def simulate_json_request(self, *args, **kwargs):
        result = self.simulate_request(*args, decode='utf-8', **kwargs)
        return json.loads(result)


class TestRequestTimeMiddleware(TestMiddleware):

    def test_skip_process_resource(self):
        global context
        self.api = falcon.API(middleware=[RequestTimeMiddleware()])

        self.api.add_route('/', MiddlewareClassResource())

        self.simulate_request('/404')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)
        self.assertIn('start_time', context)
        self.assertNotIn('mid_time', context)
        self.assertIn('end_time', context)
        self.assertFalse(context['req_succeeded'])

    def test_add_invalid_middleware(self):
        """Test than an invalid class can not be added as middleware"""
        class InvalidMiddleware():
            def process_request(self, *args):
                pass

        mw_list = [RequestTimeMiddleware(), InvalidMiddleware]
        self.assertRaises(AttributeError, falcon.API, middleware=mw_list)
        mw_list = [RequestTimeMiddleware(), 'InvalidMiddleware']
        self.assertRaises(TypeError, falcon.API, middleware=mw_list)
        mw_list = [{'process_request': 90}]
        self.assertRaises(TypeError, falcon.API, middleware=mw_list)

    def test_response_middleware_raises_exception(self):
        """Test that error in response middleware is propagated up"""
        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[RaiseErrorMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.assertRaises(Exception, self.simulate_request, self.test_route)

    def test_log_get_request(self):
        """Test that Log middleware is executed"""
        global context
        self.api = falcon.API(middleware=[RequestTimeMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_json_request(self.test_route)
        self.assertEqual(_EXPECTED_BODY, body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        self.assertIn('start_time', context)
        self.assertIn('mid_time', context)
        self.assertIn('end_time', context)
        self.assertTrue(context['mid_time'] >= context['start_time'],
                        'process_resource not executed after request')
        self.assertTrue(context['end_time'] >= context['start_time'],
                        'process_response not executed after request')

        self.assertTrue(context['req_succeeded'])


class TestTransactionIdMiddleware(TestMiddleware):

    def test_generate_trans_id_with_request(self):
        """Test that TransactionIdmiddleware is executed"""
        global context
        self.api = falcon.API(middleware=TransactionIdMiddleware())

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_json_request(self.test_route)
        self.assertEqual(_EXPECTED_BODY, body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn('transaction_id', context)
        self.assertEqual('unique-req-id', context['transaction_id'])


class TestSeveralMiddlewares(TestMiddleware):

    def test_generate_trans_id_and_time_with_request(self):
        global context
        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RequestTimeMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_json_request(self.test_route)
        self.assertEqual(_EXPECTED_BODY, body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn('transaction_id', context)
        self.assertEqual('unique-req-id', context['transaction_id'])
        self.assertIn('start_time', context)
        self.assertIn('mid_time', context)
        self.assertIn('end_time', context)
        self.assertTrue(context['mid_time'] >= context['start_time'],
                        'process_resource not executed after request')
        self.assertTrue(context['end_time'] >= context['start_time'],
                        'process_response not executed after request')

    def test_legacy_middleware_called_with_correct_args(self):
        global context
        self.api = falcon.API(middleware=[ExecutedFirstMiddleware()])
        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)
        self.assertIsInstance(context['req'], falcon.Request)
        self.assertIsInstance(context['resp'], falcon.Response)
        self.assertIsInstance(context['resource'], MiddlewareClassResource)

    def test_middleware_execution_order(self):
        global context
        self.api = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                          ExecutedLastMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_json_request(self.test_route)
        self.assertEqual(_EXPECTED_BODY, body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        # as the method registration is in a list, the order also is
        # tested
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])

    def test_multiple_reponse_mw_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        context['req_succeeded'] = []

        class RaiseStatusMiddleware(object):
            def process_response(self, req, resp, resource):
                raise falcon.HTTPStatus(falcon.HTTP_201)

        class RaiseErrorMiddleware(object):
            def process_response(self, req, resp, resource):
                raise falcon.HTTPError(falcon.HTTP_748)

        class ProcessResponseMiddleware(object):
            def process_response(self, req, resp, resource, req_succeeded):
                context['executed_methods'].append('process_response')
                context['req_succeeded'].append(req_succeeded)

        self.api = falcon.API(middleware=[ProcessResponseMiddleware(),
                                          RaiseErrorMiddleware(),
                                          ProcessResponseMiddleware(),
                                          RaiseStatusMiddleware(),
                                          ProcessResponseMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())
        self.simulate_request(self.test_route)

        self.assertEqual(self.srmock.status, falcon.HTTP_748)

        expected_methods = ['process_response'] * 3
        self.assertEqual(context['executed_methods'], expected_methods)
        self.assertEqual(context['req_succeeded'], [True, False, False])

    def test_inner_mw_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RequestTimeMiddleware(),
                                          RaiseErrorMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.assertRaises(Exception, self.simulate_request, self.test_route)

        # RequestTimeMiddleware process_response should be executed
        self.assertIn('transaction_id', context)
        self.assertIn('start_time', context)
        self.assertNotIn('mid_time', context)
        self.assertIn('end_time', context)

    def test_inner_mw_with_ex_handler_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp, resource):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RequestTimeMiddleware(),
                                          RaiseErrorMiddleware()])

        def handler(ex, req, resp, params):
            context['error_handler'] = True

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # RequestTimeMiddleware process_response should be executed
        self.assertIn('transaction_id', context)
        self.assertIn('start_time', context)
        self.assertNotIn('mid_time', context)
        self.assertIn('end_time', context)
        self.assertIn('error_handler', context)

    def test_outer_mw_with_ex_handler_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RaiseErrorMiddleware(),
                                          RequestTimeMiddleware()])

        def handler(ex, req, resp, params):
            context['error_handler'] = True

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # Any mw is executed now...
        self.assertIn('transaction_id', context)
        self.assertNotIn('start_time', context)
        self.assertNotIn('mid_time', context)
        self.assertNotIn('end_time', context)
        self.assertIn('error_handler', context)

    def test_order_mw_executed_when_exception_in_resp(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                          RaiseErrorMiddleware(),
                                          ExecutedLastMiddleware()])

        def handler(ex, req, resp, params):
            pass

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])

    def test_order_mw_executed_when_exception_in_req(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                          RaiseErrorMiddleware(),
                                          ExecutedLastMiddleware()])

        def handler(ex, req, resp, params):
            pass

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedFirstMiddleware.process_response'
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])

    def test_order_mw_executed_when_exception_in_rsrc(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_resource(self, req, resp, resource):
                raise Exception('Always fail')

        self.api = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                          RaiseErrorMiddleware(),
                                          ExecutedLastMiddleware()])

        def handler(ex, req, resp, params):
            pass

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])


class TestRemoveBasePathMiddleware(TestMiddleware):

    def test_base_path_is_removed_before_routing(self):
        """Test that RemoveBasePathMiddleware is executed before routing"""
        self.api = falcon.API(middleware=RemoveBasePathMiddleware())

        # We dont include /base_path as it will be removed in middleware
        self.api.add_route('/sub_path', MiddlewareClassResource())

        body = self.simulate_json_request('/base_path/sub_path')
        self.assertEqual(_EXPECTED_BODY, body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.simulate_request('/base_pathIncorrect/sub_path')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)


class TestResourceMiddleware(TestMiddleware):

    def test_can_access_resource_params(self):
        """Test that params can be accessed from within process_resource"""
        global context

        class Resource:
            def on_get(self, req, resp, **params):
                resp.body = json.dumps(params)

        self.api = falcon.API(middleware=AccessParamsMiddleware())
        self.api.add_route('/path/{id}', Resource())
        body = self.simulate_json_request('/path/22')

        self.assertIn('params', context)
        self.assertTrue(context['params'])
        self.assertEqual(context['params']['id'], '22')
        self.assertEqual(body, {'added': True, 'id': '22'})


class TestErrorHandling(TestMiddleware):

    def setUp(self):
        super(TestErrorHandling, self).setUp()

        self.mw = CaptureResponseMiddleware()

        self.api = falcon.API(middleware=self.mw)
        self.api.add_route('/', MiddlewareClassResource())

    def test_error_composed_before_resp_middleware_called(self):
        self.simulate_request('/', method='POST')
        self.assertEqual(self.srmock.status, falcon.HTTP_403)
        self.assertEqual(self.mw.resp.status, self.srmock.status)

        composed_body = json.loads(self.mw.resp.body)
        self.assertEqual(composed_body['title'], self.srmock.status)

        self.assertFalse(self.mw.req_succeeded)

        # NOTE(kgriffs): Sanity-check the other params passed to
        # process_response()
        self.assertIsInstance(self.mw.req, falcon.Request)
        self.assertIsInstance(self.mw.resource, MiddlewareClassResource)

    def test_http_status_raised_from_error_handler(self):
        def _http_error_handler(error, req, resp, params):
            raise falcon.HTTPStatus(falcon.HTTP_201)

        # NOTE(kgriffs): This will take precedence over the default
        # handler for facon.HTTPError.
        self.api.add_error_handler(falcon.HTTPError, _http_error_handler)

        self.simulate_request('/', method='POST')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertEqual(self.mw.resp.status, self.srmock.status)
