import functools
import json

import falcon
from falcon import testing


# --------------------------------------------------------------------
# Hooks
# --------------------------------------------------------------------


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


# NOTE(kgriffs): Use partial methods for these next two in order
# to make sure we handle that correctly.
def things_in_the_head(header, value, req, resp, params):
    resp.set_header(header, value)


bunnies_in_the_head = functools.partial(things_in_the_head,
                                        'X-Bunnies', 'fluffy')

cuteness_in_the_head = functools.partial(things_in_the_head,
                                         'X-Cuteness', 'cute')


def fluffiness_in_the_head(req, resp):
    resp.set_header('X-Fluffiness', 'fluffy')


def cuteness_in_the_head(req, resp):
    resp.set_header('X-Cuteness', 'cute')


# --------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------


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

    @falcon.after(fluffiness_in_the_head)
    @falcon.after(cuteness_in_the_head)
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


# --------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------


class TestHooks(testing.TestCase):

    def setUp(self):
        super(TestHooks, self).setUp()

        self.resource = WrappedRespondersResource()
        self.api.add_route('/', self.resource)

        self.wrapped_resource = WrappedClassResource()
        self.api.add_route('/wrapped', self.wrapped_resource)

        self.wrapped_resource_aware = ClassResourceWithAwareHooks()
        self.api.add_route('/wrapped_aware', self.wrapped_resource_aware)

    def test_output_validator(self):
        result = self.simulate_get()
        self.assertEqual(result.status_code, 723)
        self.assertEqual(result.text, '{\n    "title": "Tricky"\n}')

    def test_serializer(self):
        result = self.simulate_put()
        self.assertEqual('{"animal": "falcon"}', result.text)

    def test_hook_as_callable_class(self):
        result = self.simulate_post()
        self.assertEqual('smart', result.text)

    def test_wrapped_resource(self):
        result = self.simulate_get('/wrapped')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.text, 'fluffy and cute', )

        result = self.simulate_head('/wrapped')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers['X-Fluffiness'], 'fluffy')
        self.assertEqual(result.headers['X-Cuteness'], 'cute')

        result = self.simulate_post('/wrapped')
        self.assertEqual(result.status_code, 405)

        result = self.simulate_patch('/wrapped')
        self.assertEqual(result.status_code, 405)

        # Decorator should not affect the default on_options responder
        result = self.simulate_options('/wrapped')
        self.assertEqual(result.status_code, 204)
        self.assertFalse(result.text)

    def test_wrapped_resource_with_hooks_aware_of_resource(self):
        expected = 'fluffy and cute'

        result = self.simulate_get('/wrapped_aware')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(expected, result.text)

        for test in (self.simulate_head, self.simulate_put, self.simulate_post):
            result = test('/wrapped_aware')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(self.wrapped_resource_aware.resp.body, expected)

        result = self.simulate_patch('/wrapped_aware')
        self.assertEqual(result.status_code, 405)

        # Decorator should not affect the default on_options responder
        result = self.simulate_options('/wrapped_aware')
        self.assertEqual(result.status_code, 204)
        self.assertFalse(result.text)
