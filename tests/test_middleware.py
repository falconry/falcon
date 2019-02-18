from datetime import datetime
import json

import pytest

import falcon
import falcon.testing as testing

_EXPECTED_BODY = {u'status': u'ok'}

context = {'executed_methods': []}
TEST_ROUTE = '/test_path'


class CaptureResponseMiddleware(object):

    def process_response(self, req, resp, resource, req_succeeded):
        self.req = req
        self.resp = resp
        self.resource = resource
        self.req_succeeded = req_succeeded


class CaptureRequestMiddleware(object):

    def process_request(self, req, resp):
        self.req = req


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

    def process_resource(self, req, resp, resource, params):
        global context
        context['resource_transaction_id'] = 'unique-req-id-2'

    def process_response(self, req, resp, resource, req_succeeded):
        pass


class ExecutedFirstMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['executed_methods'].append(
            '{}.{}'.format(self.__class__.__name__, 'process_request'))

    def process_resource(self, req, resp, resource, params):
        global context
        context['executed_methods'].append(
            '{}.{}'.format(self.__class__.__name__, 'process_resource'))

    # NOTE(kgriffs): This also tests that the framework can continue to
    # call process_response() methods that do not have a 'req_succeeded'
    # arg.
    def process_response(self, req, resp, resource, req_succeeded):
        global context
        context['executed_methods'].append(
            '{}.{}'.format(self.__class__.__name__, 'process_response'))

        context['req'] = req
        context['resp'] = resp
        context['resource'] = resource


class ExecutedLastMiddleware(ExecutedFirstMiddleware):
    pass


class RemoveBasePathMiddleware(object):

    def process_request(self, req, resp):
        req.path = req.path.replace('/base_path', '', 1)


class ResponseCacheMiddlware(object):

    PROCESS_REQUEST_CACHED_BODY = {'cached': True}
    PROCESS_RESOURCE_CACHED_BODY = {'cached': True, 'resource': True}

    def process_request(self, req, resp):
        if req.path == '/cached':
            resp.media = self.PROCESS_REQUEST_CACHED_BODY
            resp.complete = True
            return

    def process_resource(self, req, resp, resource, params):
        if req.path == '/cached/resource':
            resp.media = self.PROCESS_RESOURCE_CACHED_BODY
            resp.complete = True
            return


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


class EmptySignatureMiddleware(object):

    def process_request(self):
        pass

    def process_response(self):
        pass


class TestMiddleware(object):
    def setup_method(self, method):
        # Clear context
        global context
        context = {'executed_methods': []}


class TestRequestTimeMiddleware(TestMiddleware):

    def test_skip_process_resource(self):
        global context
        app = falcon.API(middleware=[RequestTimeMiddleware()])

        app.add_route('/', MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/404')
        assert response.status == falcon.HTTP_404
        assert 'start_time' in context
        assert 'mid_time' not in context
        assert 'end_time' in context
        assert not context['req_succeeded']

    def test_add_invalid_middleware(self):
        """Test than an invalid class can not be added as middleware"""
        class InvalidMiddleware():
            def process_request(self, *args):
                pass

        mw_list = [RequestTimeMiddleware(), InvalidMiddleware]
        with pytest.raises(AttributeError):
            falcon.API(middleware=mw_list)
        mw_list = [RequestTimeMiddleware(), 'InvalidMiddleware']
        with pytest.raises(TypeError):
            falcon.API(middleware=mw_list)
        mw_list = [{'process_request': 90}]
        with pytest.raises(TypeError):
            falcon.API(middleware=mw_list)

    def test_response_middleware_raises_exception(self):
        """Test that error in response middleware is propagated up"""
        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception('Always fail')

        app = falcon.API(middleware=[RaiseErrorMiddleware()])

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        with pytest.raises(Exception):
            client.simulate_request(path=TEST_ROUTE)

    @pytest.mark.parametrize('independent_middleware', [True, False])
    def test_log_get_request(self, independent_middleware):
        """Test that Log middleware is executed"""
        global context
        app = falcon.API(middleware=[RequestTimeMiddleware()],
                         independent_middleware=independent_middleware)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path=TEST_ROUTE)
        assert _EXPECTED_BODY == response.json
        assert response.status == falcon.HTTP_200

        assert 'start_time' in context
        assert 'mid_time' in context
        assert 'end_time' in context
        assert context['mid_time'] >= context['start_time'], \
            'process_resource not executed after request'
        assert context['end_time'] >= context['start_time'], \
            'process_response not executed after request'

        assert context['req_succeeded']


class TestTransactionIdMiddleware(TestMiddleware):
    def test_generate_trans_id_with_request(self):
        """Test that TransactionIdmiddleware is executed"""
        global context
        app = falcon.API(middleware=TransactionIdMiddleware())

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path=TEST_ROUTE)
        assert _EXPECTED_BODY == response.json
        assert response.status == falcon.HTTP_200
        assert 'transaction_id' in context
        assert 'unique-req-id' == context['transaction_id']


class TestSeveralMiddlewares(TestMiddleware):
    @pytest.mark.parametrize('independent_middleware', [True, False])
    def test_generate_trans_id_and_time_with_request(self, independent_middleware):
        # NOTE(kgriffs): We test both so that we can cover the code paths
        # where only a single middleware method is implemented by a
        # component.
        creq = CaptureRequestMiddleware()
        cresp = CaptureResponseMiddleware()

        global context
        app = falcon.API(independent_middleware=independent_middleware,
                         middleware=[TransactionIdMiddleware(),
                                     RequestTimeMiddleware(),
                                     creq,
                                     cresp])

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path=TEST_ROUTE)
        assert _EXPECTED_BODY == response.json
        assert response.status == falcon.HTTP_200
        assert 'transaction_id' in context
        assert 'unique-req-id' == context['transaction_id']
        assert 'start_time' in context
        assert 'mid_time' in context
        assert 'end_time' in context
        assert context['mid_time'] >= context['start_time'], \
            'process_resource not executed after request'
        assert context['end_time'] >= context['start_time'], \
            'process_response not executed after request'

    def test_legacy_middleware_called_with_correct_args(self):
        global context
        app = falcon.API(middleware=[ExecutedFirstMiddleware()])
        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)
        assert isinstance(context['req'], falcon.Request)
        assert isinstance(context['resp'], falcon.Response)
        assert isinstance(context['resource'], MiddlewareClassResource)

    def test_middleware_execution_order(self):
        global context
        app = falcon.API(independent_middleware=False,
                         middleware=[ExecutedFirstMiddleware(),
                                     ExecutedLastMiddleware()])

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path=TEST_ROUTE)
        assert _EXPECTED_BODY == response.json
        assert response.status == falcon.HTTP_200
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
        assert expectedExecutedMethods == context['executed_methods']

    def test_independent_middleware_execution_order(self):
        global context
        app = falcon.API(independent_middleware=True,
                         middleware=[ExecutedFirstMiddleware(),
                                     ExecutedLastMiddleware()])

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path=TEST_ROUTE)
        assert _EXPECTED_BODY == response.json
        assert response.status == falcon.HTTP_200
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
        assert expectedExecutedMethods == context['executed_methods']

    def test_multiple_reponse_mw_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        context['req_succeeded'] = []

        class RaiseStatusMiddleware(object):
            def process_response(self, req, resp, resource, req_succeeded):
                raise falcon.HTTPStatus(falcon.HTTP_201)

        class RaiseErrorMiddleware(object):
            def process_response(self, req, resp, resource, req_succeeded):
                raise falcon.HTTPError(falcon.HTTP_748)

        class ProcessResponseMiddleware(object):
            def process_response(self, req, resp, resource, req_succeeded):
                context['executed_methods'].append('process_response')
                context['req_succeeded'].append(req_succeeded)

        app = falcon.API(middleware=[ProcessResponseMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ProcessResponseMiddleware(),
                                     RaiseStatusMiddleware(),
                                     ProcessResponseMiddleware()])

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path=TEST_ROUTE)

        assert response.status == falcon.HTTP_748

        expected_methods = ['process_response'] * 3
        assert context['executed_methods'] == expected_methods
        assert context['req_succeeded'] == [True, False, False]

    def test_inner_mw_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        app = falcon.API(middleware=[TransactionIdMiddleware(),
                                     RequestTimeMiddleware(),
                                     RaiseErrorMiddleware()])

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        with pytest.raises(Exception):
            client.simulate_request(path=TEST_ROUTE)

        # RequestTimeMiddleware process_response should be executed
        assert 'transaction_id' in context
        assert 'start_time' in context
        assert 'mid_time' not in context
        assert 'end_time' in context

    def test_inner_mw_with_ex_handler_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp, resource):
                raise Exception('Always fail')

        app = falcon.API(middleware=[TransactionIdMiddleware(),
                                     RequestTimeMiddleware(),
                                     RaiseErrorMiddleware()])

        def handler(req, resp, ex, params):
            context['error_handler'] = True

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # RequestTimeMiddleware process_response should be executed
        assert 'transaction_id' in context
        assert 'start_time' in context
        assert 'mid_time' not in context
        assert 'end_time' in context
        assert 'error_handler' in context

    def test_outer_mw_with_ex_handler_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        app = falcon.API(middleware=[TransactionIdMiddleware(),
                                     RaiseErrorMiddleware(),
                                     RequestTimeMiddleware()])

        def handler(req, resp, ex, params):
            context['error_handler'] = True

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # Any mw is executed now...
        assert 'transaction_id' in context
        assert 'start_time' not in context
        assert 'mid_time' not in context
        assert 'end_time' in context
        assert 'error_handler' in context

    def test_order_mw_executed_when_exception_in_resp(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception('Always fail')

        app = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ExecutedLastMiddleware()])

        def handler(req, resp, ex, params):
            pass

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        assert expectedExecutedMethods == context['executed_methods']

    def test_order_independent_mw_executed_when_exception_in_resp(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception('Always fail')

        app = falcon.API(independent_middleware=True,
                         middleware=[ExecutedFirstMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ExecutedLastMiddleware()])

        def handler(req, resp, ex, params):
            pass

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        assert expectedExecutedMethods == context['executed_methods']

    def test_order_mw_executed_when_exception_in_req(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        app = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ExecutedLastMiddleware()])

        def handler(req, resp, ex, params):
            pass

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        assert expectedExecutedMethods == context['executed_methods']

    def test_order_independent_mw_executed_when_exception_in_req(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception('Always fail')

        app = falcon.API(independent_middleware=True,
                         middleware=[ExecutedFirstMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ExecutedLastMiddleware()])

        def handler(req, resp, ex, params):
            pass

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # All response middleware still executed...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        assert expectedExecutedMethods == context['executed_methods']

    def test_order_mw_executed_when_exception_in_rsrc(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_resource(self, req, resp, resource):
                raise Exception('Always fail')

        app = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ExecutedLastMiddleware()])

        def handler(req, resp, ex, params):
            pass

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        assert expectedExecutedMethods == context['executed_methods']

    def test_order_independent_mw_executed_when_exception_in_rsrc(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_resource(self, req, resp, resource):
                raise Exception('Always fail')

        app = falcon.API(independent_middleware=True,
                         middleware=[ExecutedFirstMiddleware(),
                                     RaiseErrorMiddleware(),
                                     ExecutedLastMiddleware()])

        def handler(req, resp, ex, params):
            pass

        app.add_error_handler(Exception, handler)

        app.add_route(TEST_ROUTE, MiddlewareClassResource())
        client = testing.TestClient(app)

        client.simulate_request(path=TEST_ROUTE)

        # Any mw is executed now...
        expectedExecutedMethods = [
            'ExecutedFirstMiddleware.process_request',
            'ExecutedLastMiddleware.process_request',
            'ExecutedFirstMiddleware.process_resource',
            'ExecutedLastMiddleware.process_response',
            'ExecutedFirstMiddleware.process_response'
        ]
        assert expectedExecutedMethods == context['executed_methods']


class TestRemoveBasePathMiddleware(TestMiddleware):
    def test_base_path_is_removed_before_routing(self):
        """Test that RemoveBasePathMiddleware is executed before routing"""
        app = falcon.API(middleware=RemoveBasePathMiddleware())

        # We dont include /base_path as it will be removed in middleware
        app.add_route('/sub_path', MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/base_path/sub_path')
        assert _EXPECTED_BODY == response.json
        assert response.status == falcon.HTTP_200
        response = client.simulate_request(path='/base_pathIncorrect/sub_path')
        assert response.status == falcon.HTTP_404


class TestResourceMiddleware(TestMiddleware):

    @pytest.mark.parametrize('independent_middleware', [True, False])
    def test_can_access_resource_params(self, independent_middleware):
        """Test that params can be accessed from within process_resource"""
        global context

        class Resource:
            def on_get(self, req, resp, **params):
                resp.body = json.dumps(params)

        app = falcon.API(middleware=AccessParamsMiddleware(),
                         independent_middleware=independent_middleware)
        app.add_route('/path/{id}', Resource())
        client = testing.TestClient(app)
        response = client.simulate_request(path='/path/22')

        assert 'params' in context
        assert context['params']
        assert context['params']['id'] == '22'
        assert response.json == {'added': True, 'id': '22'}


class TestEmptySignatureMiddleware(TestMiddleware):
    def test_dont_need_params_in_signature(self):
        """
        Verify that we don't need parameters in the process_* signatures (for
        side-effect-only middlewares, mostly). Makes no difference on py27
        but does affect py36.

        https://github.com/falconry/falcon/issues/1254
        """
        falcon.API(middleware=EmptySignatureMiddleware())


class TestErrorHandling(TestMiddleware):
    def test_error_composed_before_resp_middleware_called(self):
        mw = CaptureResponseMiddleware()
        app = falcon.API(middleware=mw)
        app.add_route('/', MiddlewareClassResource())
        client = testing.TestClient(app)

        response = client.simulate_request(path='/', method='POST')
        assert response.status == falcon.HTTP_403
        assert mw.resp.status == response.status

        composed_body = json.loads(mw.resp.body)
        assert composed_body['title'] == response.status

        assert not mw.req_succeeded

        # NOTE(kgriffs): Sanity-check the other params passed to
        # process_response()
        assert isinstance(mw.req, falcon.Request)
        assert isinstance(mw.resource, MiddlewareClassResource)

    def test_http_status_raised_from_error_handler(self):
        mw = CaptureResponseMiddleware()
        app = falcon.API(middleware=mw)
        app.add_route('/', MiddlewareClassResource())
        client = testing.TestClient(app)

        def _http_error_handler(error, req, resp, params):
            raise falcon.HTTPStatus(falcon.HTTP_201)

        # NOTE(kgriffs): This will take precedence over the default
        # handler for facon.HTTPError.
        app.add_error_handler(falcon.HTTPError, _http_error_handler)

        response = client.simulate_request(path='/', method='POST')
        assert response.status == falcon.HTTP_201
        assert mw.resp.status == response.status


class TestShortCircuiting(TestMiddleware):
    def setup_method(self, method):
        super(TestShortCircuiting, self).setup_method(method)

    def _make_client(self, independent_middleware=True):
        mw = [
            RequestTimeMiddleware(),
            ResponseCacheMiddlware(),
            TransactionIdMiddleware(),
        ]
        app = falcon.API(middleware=mw, independent_middleware=independent_middleware)
        app.add_route('/', MiddlewareClassResource())
        app.add_route('/cached', MiddlewareClassResource())
        app.add_route('/cached/resource', MiddlewareClassResource())

        return testing.TestClient(app)

    def test_process_request_not_cached(self):
        response = self._make_client().simulate_get('/')
        assert response.status == falcon.HTTP_200
        assert response.json == _EXPECTED_BODY
        assert 'transaction_id' in context
        assert 'resource_transaction_id' in context
        assert 'mid_time' in context
        assert 'end_time' in context

    @pytest.mark.parametrize('independent_middleware', [True, False])
    def test_process_request_cached(self, independent_middleware):
        response = self._make_client(independent_middleware).simulate_get('/cached')
        assert response.status == falcon.HTTP_200
        assert response.json == ResponseCacheMiddlware.PROCESS_REQUEST_CACHED_BODY

        # NOTE(kgriffs): Since TransactionIdMiddleware was ordered after
        # ResponseCacheMiddlware, the response short-circuiting should have
        # skipped it.
        assert 'transaction_id' not in context
        assert 'resource_transaction_id' not in context

        # NOTE(kgriffs): RequestTimeMiddleware only adds this in
        # process_resource(), which should be skipped when
        # ResponseCacheMiddlware sets resp.completed = True in
        # process_request().
        assert 'mid_time' not in context

        # NOTE(kgriffs): Short-circuiting does not affect process_response()
        assert 'end_time' in context

    @pytest.mark.parametrize('independent_middleware', [True, False])
    def test_process_resource_cached(self, independent_middleware):
        response = self._make_client(independent_middleware).simulate_get('/cached/resource')
        assert response.status == falcon.HTTP_200
        assert response.json == ResponseCacheMiddlware.PROCESS_RESOURCE_CACHED_BODY

        # NOTE(kgriffs): This should be present because it is added in
        # process_request(), but the short-circuit does not occur until
        # process_resource().
        assert 'transaction_id' in context

        # NOTE(kgriffs): Since TransactionIdMiddleware was ordered after
        # ResponseCacheMiddlware, the response short-circuiting should have
        # skipped it.
        assert 'resource_transaction_id' not in context

        # NOTE(kgriffs): RequestTimeMiddleware only adds this in
        # process_resource(), which will not be skipped in this case because
        # RequestTimeMiddleware is ordered before ResponseCacheMiddlware.
        assert 'mid_time' in context

        # NOTE(kgriffs): Short-circuiting does not affect process_response()
        assert 'end_time' in context
