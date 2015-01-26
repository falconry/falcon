import falcon
import falcon.testing as testing
from datetime import datetime

context = {'executed_methods': []}


class RequestTimeMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['start_time'] = datetime.utcnow()

    def process_resource(self, req, resp, resource):
        global context
        context['mid_time'] = datetime.utcnow()

    def process_response(self, req, resp, resource):
        global context
        context['end_time'] = datetime.utcnow()


class TransactionIdMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['transaction_id'] = 'unique-req-id'


class ExecutedFirstMiddleware(object):

    def process_request(self, req, resp):
        global context
        context['executed_methods'].append(
            '{0}.{1}'.format(self.__class__.__name__, 'process_request'))

    def process_resource(self, req, resp, resource):
        global context
        context['executed_methods'].append(
            '{0}.{1}'.format(self.__class__.__name__, 'process_resource'))

    def process_response(self, req, resp, resource):
        global context
        context['executed_methods'].append(
            '{0}.{1}'.format(self.__class__.__name__, 'process_response'))


class ExecutedLastMiddleware(ExecutedFirstMiddleware):
    pass


class RemoveBasePathMiddleware(object):

    def process_request(self, req, resp):
        req.path = req.path.replace('/base_path', '', 1)


class MiddlewareClassResource(object):

    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = {'status': 'ok'}


class TestMiddleware(testing.TestBase):

    def setUp(self):
        # Clear context
        global context
        context = {'executed_methods': []}
        testing.TestBase.setUp(self)


class TestRequestTimeMiddleware(TestMiddleware):

    def test_add_invalid_middleware(self):
        """Test than an invalid class can not be added as middleware"""
        class InvalidMiddleware():
            def process_request(self, *args):
                pass

        mw_list = [RequestTimeMiddleware(), InvalidMiddleware]
        self.assertRaises(AttributeError, falcon.API, middleware=mw_list)
        mw_list = [RequestTimeMiddleware(), "InvalidMiddleware"]
        self.assertRaises(TypeError, falcon.API, middleware=mw_list)
        mw_list = [{'process_request': 90}]
        self.assertRaises(TypeError, falcon.API, middleware=mw_list)

    def test_response_middleware_raises_exception(self):
        """Test that error in response middleware is propagated up"""
        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception("Always fail")

        self.api = falcon.API(middleware=[RaiseErrorMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.assertRaises(Exception, self.simulate_request, self.test_route)

    def test_log_get_request(self):
        """Test that Log middleware is executed"""
        global context
        self.api = falcon.API(middleware=[RequestTimeMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([{'status': 'ok'}], body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn("start_time", context)
        self.assertIn("mid_time", context)
        self.assertIn("end_time", context)
        self.assertTrue(context['mid_time'] > context['start_time'],
                        "process_resource not executed after request")
        self.assertTrue(context['end_time'] > context['start_time'],
                        "process_response not executed after request")


class TestTransactionIdMiddleware(TestMiddleware):

    def test_generate_trans_id_with_request(self):
        """Test that TransactionIdmiddleware is executed"""
        global context
        self.api = falcon.API(middleware=TransactionIdMiddleware())

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([{'status': 'ok'}], body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn("transaction_id", context)
        self.assertEqual("unique-req-id", context['transaction_id'])


class TestSeveralMiddlewares(TestMiddleware):

    def test_generate_trans_id_and_time_with_request(self):
        global context
        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RequestTimeMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([{'status': 'ok'}], body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn("transaction_id", context)
        self.assertEqual("unique-req-id", context['transaction_id'])
        self.assertIn("start_time", context)
        self.assertIn("mid_time", context)
        self.assertIn("end_time", context)
        self.assertTrue(context['mid_time'] > context['start_time'],
                        "process_resource not executed after request")
        self.assertTrue(context['end_time'] > context['start_time'],
                        "process_response not executed after request")

    def test_middleware_execution_order(self):
        global context
        self.api = falcon.API(middleware=[ExecutedFirstMiddleware(),
                                          ExecutedLastMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        body = self.simulate_request(self.test_route)
        self.assertEqual([{'status': 'ok'}], body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        # as the method registration is in a list, the order also is
        # tested
        expectedExecutedMethods = [
            "ExecutedFirstMiddleware.process_request",
            "ExecutedLastMiddleware.process_request",
            "ExecutedFirstMiddleware.process_resource",
            "ExecutedLastMiddleware.process_resource",
            "ExecutedLastMiddleware.process_response",
            "ExecutedFirstMiddleware.process_response"
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])

    def test_inner_mw_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception("Always fail")

        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RequestTimeMiddleware(),
                                          RaiseErrorMiddleware()])

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.assertRaises(Exception, self.simulate_request, self.test_route)

        # RequestTimeMiddleware process_response should be executed
        self.assertIn("transaction_id", context)
        self.assertIn("start_time", context)
        self.assertNotIn("mid_time", context)
        self.assertIn("end_time", context)

    def test_inner_mw_with_ex_handler_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp, resource):
                raise Exception("Always fail")

        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RequestTimeMiddleware(),
                                          RaiseErrorMiddleware()])

        def handler(ex, req, resp, params):
            context['error_handler'] = True

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # RequestTimeMiddleware process_response should be executed
        self.assertIn("transaction_id", context)
        self.assertIn("start_time", context)
        self.assertNotIn("mid_time", context)
        self.assertIn("end_time", context)
        self.assertIn("error_handler", context)

    def test_outer_mw_with_ex_handler_throw_exception(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception("Always fail")

        self.api = falcon.API(middleware=[TransactionIdMiddleware(),
                                          RaiseErrorMiddleware(),
                                          RequestTimeMiddleware()])

        def handler(ex, req, resp, params):
            context['error_handler'] = True

        self.api.add_error_handler(Exception, handler)

        self.api.add_route(self.test_route, MiddlewareClassResource())

        self.simulate_request(self.test_route)

        # Any mw is executed now...
        self.assertIn("transaction_id", context)
        self.assertNotIn("start_time", context)
        self.assertNotIn("mid_time", context)
        self.assertNotIn("end_time", context)
        self.assertIn("error_handler", context)

    def test_order_mw_executed_when_exception_in_resp(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_response(self, req, resp, resource):
                raise Exception("Always fail")

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
            "ExecutedFirstMiddleware.process_request",
            "ExecutedLastMiddleware.process_request",
            "ExecutedFirstMiddleware.process_resource",
            "ExecutedLastMiddleware.process_resource",
            "ExecutedLastMiddleware.process_response",
            "ExecutedFirstMiddleware.process_response"
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])

    def test_order_mw_executed_when_exception_in_req(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_request(self, req, resp):
                raise Exception("Always fail")

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
            "ExecutedFirstMiddleware.process_request",
            "ExecutedFirstMiddleware.process_response"
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])

    def test_order_mw_executed_when_exception_in_rsrc(self):
        """Test that error in inner middleware leaves"""
        global context

        class RaiseErrorMiddleware(object):

            def process_resource(self, req, resp, resource):
                raise Exception("Always fail")

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
            "ExecutedFirstMiddleware.process_request",
            "ExecutedLastMiddleware.process_request",
            "ExecutedFirstMiddleware.process_resource",
            "ExecutedLastMiddleware.process_response",
            "ExecutedFirstMiddleware.process_response"
        ]
        self.assertEqual(expectedExecutedMethods, context['executed_methods'])


class TestRemoveBasePathMiddleware(TestMiddleware):

    def test_base_path_is_removed_before_routing(self):
        """Test that RemoveBasePathMiddleware is executed before routing"""
        self.api = falcon.API(middleware=RemoveBasePathMiddleware())

        # We dont include /base_path as it will be removed in middleware
        self.api.add_route('/sub_path', MiddlewareClassResource())

        body = self.simulate_request('/base_path/sub_path')
        self.assertEqual([{'status': 'ok'}], body)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.simulate_request('/base_pathIncorrect/sub_path')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)
