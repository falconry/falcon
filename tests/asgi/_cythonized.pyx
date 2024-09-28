# cython: language_level=3

from collections import Counter
import time

import falcon
from falcon.media.validators.jsonschema import validate


_MESSAGE_SCHEMA = {
    'definitions': {},
    '$schema': 'http://json-schema.org/draft-07/schema#',
    '$id': 'http://example.com/root.json',
    'type': 'object',
    'title': 'The Root Schema',
    'required': ['message'],
    'properties': {
        'message': {
            '$id': '#/properties/message',
            'type': 'string',
            'title': 'The Message Schema',
            'default': '',
            'examples': ['hello world'],
            'pattern': '^(.*)$'
        }
    }
}


def nop_method(self):
    pass


async def nop_method_async(self):
    pass


class NOPClass:
    def nop_method(self):
        pass

    async def nop_method_async(self):
        pass


class TestResourceWithValidation:
    @validate(resp_schema=_MESSAGE_SCHEMA)
    async def on_get(self, req, resp):
        resp.media = {'message': 'hello world'}


class TestResourceWithScheduledJobs:
    def __init__(self):
        self.counter = Counter()

    async def on_get(self, req, resp):
        async def background_job_async():
            self.counter['backround:on_get:async'] += 1

        def background_job_sync():
            self.counter['backround:on_get:sync'] += 20

        resp.schedule(background_job_async)
        resp.schedule_sync(background_job_sync)
        resp.schedule(background_job_async)
        resp.schedule_sync(background_job_sync)


class TestResourceWithScheduledJobsAsyncRequired:
    def __init__(self):
        self.counter = Counter()

    async def on_get(self, req, resp):
        def background_job_sync():
            pass

        # NOTE(kgriffs): This will fail later since we can't detect
        #    up front that it isn't a coroutine function.
        resp.schedule(background_job_sync)


async def my_before_hook(req, resp, resource, params):
    req.context.before = 42


async def my_after_hook(req, resp, resource):
    resp.set_header('X-Answer', '42')
    resp.media = {'answer': req.context.before}


class TestResourceWithHooks:
    @falcon.before(my_before_hook)
    @falcon.after(my_after_hook)
    async def on_get(self, req, resp):
        pass
