import json

import falcon
import falcon.testing as testing


def validate_output(req, resp):
    raise falcon.HTTPError(falcon.HTTP_723, 'Tricky')


def serialize_body(req, resp):
    body = resp.body
    if body is not None:
        resp.body = json.dumps(body)
    else:
        resp.body = 'Nothing to see here. Move along.'


def fluffiness(req, resp):
    resp.body = 'fluffy'


def resource_aware_fluffiness(req, resp, resource):
    assert resource
    fluffiness(req, resp)


class ResourceAwareFluffiness(object):
    def __call__(self, req, resp, resource):
        assert resource
        fluffiness(req, resp)


def cuteness(req, resp):
    if resp.body == 'fluffy':
        resp.body += ' and cute'


def resource_aware_cuteness(req, resp, resource):
    assert resource
    cuteness(req, resp)


class Smartness(object):
    def __call__(self, req, resp):
        if resp.body:
            resp.body += ' and smart'
        else:
            resp.body = 'smart'


def fluffiness_in_the_head(req, resp):
    resp.set_header('X-Fluffiness', 'fluffy')


def cuteness_in_the_head(req, resp):
    resp.set_header('X-Cuteness', 'cute')


class WrappedRespondersResource(object):

    @falcon.after(serialize_body)
    @falcon.after(validate_output)
    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    @falcon.after(serialize_body)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp
        resp.body = {'animal': 'falcon'}

    @falcon.after(Smartness())
    def on_post(self, req, resp):
        pass


@falcon.after(cuteness)
@falcon.after(fluffiness)
class WrappedClassResource(object):

    # Test that the decorator skips non-callables
    on_post = False

    def __init__(self):
        # Test that the decorator skips non-callables
        self.on_patch = []

    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    def on_head(self, req, resp):
        self.req = req
        self.resp = resp


# NOTE(swistakm): we use both type of hooks (class and method)
# at once for the sake of simplicity
@falcon.after(resource_aware_cuteness)
class ClassResourceWithAwareHooks(object):

    # Test that the decorator skips non-callables
    on_post = False

    hook_as_class = ResourceAwareFluffiness()

    def __init__(self):
        # Test that the decorator skips non-callables
        self.on_patch = []

    @falcon.after(resource_aware_fluffiness)
    def on_get(self, req, resp):
        self._capture(req, resp)

    @falcon.after(resource_aware_fluffiness)
    def on_head(self, req, resp):
        self._capture(req, resp)

    @falcon.after(hook_as_class)
    def on_put(self, req, resp):
        self._capture(req, resp)

    @falcon.after(hook_as_class.__call__)
    def on_post(self, req, resp):
        self._capture(req, resp)

    def _capture(self, req, resp):
        self.req = req
        self.resp = resp


class ZooResource(object):

    def on_get(self, req, resp):
        self.resp = resp


class SingleResource(object):

    def on_options(self, req, resp):
        resp.status = falcon.HTTP_501


class FaultyResource(object):

    def on_get(self, req, resp):
        raise falcon.HTTPError(falcon.HTTP_743, 'Query failed')


class TestHooks(testing.TestBase):

    def before(self):
        self.resource = WrappedRespondersResource()
        self.api.add_route(self.test_route, self.resource)

        self.wrapped_resource = WrappedClassResource()
        self.api.add_route('/wrapped', self.wrapped_resource)

        self.wrapped_resource_aware = ClassResourceWithAwareHooks()
        self.api.add_route('/wrapped_aware', self.wrapped_resource_aware)

    def test_global_hook(self):
        self.assertRaises(TypeError, falcon.API, None, {})
        self.assertRaises(TypeError, falcon.API, None, 0)

        self.api = falcon.API(after=fluffiness)
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual(b'fluffy', zoo_resource.resp.body_encoded)

    def test_global_hook_is_resource_aware(self):
        self.assertRaises(TypeError, falcon.API, None, {})
        self.assertRaises(TypeError, falcon.API, None, 0)

        self.api = falcon.API(after=resource_aware_fluffiness)
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual(b'fluffy', zoo_resource.resp.body_encoded)

    def test_multiple_global_hook(self):
        self.api = falcon.API(after=[fluffiness, cuteness, Smartness()])
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route)
        self.assertEqual(b'fluffy and cute and smart',
                         zoo_resource.resp.body_encoded)

    def test_global_hook_wrap_default_on_options(self):
        self.api = falcon.API(after=fluffiness_in_the_head)
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route, method='OPTIONS')

        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        self.assertEqual('fluffy', self.srmock.headers_dict['X-Fluffiness'])

    def test_global_hook_wrap_default_405(self):
        self.api = falcon.API(after=fluffiness_in_the_head)
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route, method='POST')

        self.assertEqual(falcon.HTTP_405, self.srmock.status)
        self.assertEqual('fluffy', self.srmock.headers_dict['X-Fluffiness'])

    def test_multiple_global_hooks_wrap_default_on_options(self):
        self.api = falcon.API(after=[fluffiness_in_the_head,
                                     cuteness_in_the_head])
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route, method='OPTIONS')

        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        self.assertEqual('fluffy', self.srmock.headers_dict['X-Fluffiness'])
        self.assertEqual('cute', self.srmock.headers_dict['X-Cuteness'])

    def test_multiple_global_hooks_wrap_default_405(self):
        self.api = falcon.API(after=[fluffiness_in_the_head,
                                     cuteness_in_the_head])
        zoo_resource = ZooResource()

        self.api.add_route(self.test_route, zoo_resource)

        self.simulate_request(self.test_route, method='POST')

        self.assertEqual(falcon.HTTP_405, self.srmock.status)
        self.assertEqual('fluffy', self.srmock.headers_dict['X-Fluffiness'])
        self.assertEqual('cute', self.srmock.headers_dict['X-Cuteness'])

    def test_global_after_hooks_run_after_exception(self):
        self.api = falcon.API(after=[fluffiness,
                                     resource_aware_cuteness,
                                     Smartness()])

        self.api.add_route(self.test_route, FaultyResource())

        actual_body = self.simulate_request(self.test_route, decode='utf-8')
        self.assertEqual(falcon.HTTP_743, self.srmock.status)
        self.assertEqual(actual_body, u'fluffy and cute and smart')

    def test_output_validator(self):
        self.simulate_request(self.test_route)
        self.assertEqual(falcon.HTTP_723, self.srmock.status)

        expected = b'{\n    "title": "Tricky"\n}'
        self.assertEqual(expected, self.resource.resp.body_encoded)

    def test_serializer(self):
        self.simulate_request(self.test_route, method='PUT')

        actual_body = self.resource.resp.body_encoded
        self.assertEqual(b'{"animal": "falcon"}', actual_body)

    def test_hook_as_callable_class(self):
        actual_body = self.simulate_request(self.test_route, method='POST',
                                            decode='utf-8')

        self.assertEqual(u'smart', actual_body)

    def test_wrapped_resource(self):
        expected = b'fluffy and cute'

        self.simulate_request('/wrapped')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(expected, self.wrapped_resource.resp.body_encoded)

        self.simulate_request('/wrapped', method='HEAD')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_request('/wrapped', method='POST')
        self.assertEqual(falcon.HTTP_405, self.srmock.status)

        self.simulate_request('/wrapped', method='PATCH')
        self.assertEqual(falcon.HTTP_405, self.srmock.status)

        # decorator does not affect the default on_options
        body = self.simulate_request('/wrapped', method='OPTIONS')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        self.assertEqual([], body)

    def test_wrapped_resource_with_hooks_aware_of_resource(self):
        expected = b'fluffy and cute'

        self.simulate_request('/wrapped_aware')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(expected,
                         self.wrapped_resource_aware.resp.body_encoded)

        for method in ('HEAD', 'PUT', 'POST'):
            self.simulate_request('/wrapped_aware', method=method)
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual(expected,
                             self.wrapped_resource_aware.resp.body_encoded)

        self.simulate_request('/wrapped_aware', method='PATCH')
        self.assertEqual(falcon.HTTP_405, self.srmock.status)

        # decorator does not affect the default on_options
        body = self.simulate_request('/wrapped_aware', method='OPTIONS')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        self.assertEqual([], body)

    def test_customized_options(self):
        self.api = falcon.API(after=fluffiness)

        self.api.add_route('/one', SingleResource())

        body = self.simulate_request('/one', method='OPTIONS')
        self.assertEqual(falcon.HTTP_501, self.srmock.status)
        self.assertEqual([b'fluffy'], body)
        self.assertNotIn('allow', self.srmock.headers_dict)
