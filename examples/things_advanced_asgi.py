# examples/things_advanced_asgi.py

import logging
import time
import uuid

import httpx

import falcon
import falcon.asgi


class StorageEngine:
    async def get_things(self, marker, limit):
        return [{'id': str(uuid.uuid4()), 'color': 'green'}]

    async def add_thing(self, thing):
        thing['id'] = str(uuid.uuid4())
        return thing


class StorageError(Exception):
    @staticmethod
    async def handle(req, resp, ex, params):
        # TODO(mmustafasenoglu): Log the error, clean up, etc. before raising
        raise falcon.HTTPInternalServerError()


class SinkAdapter:
    engines = {
        'ddg': 'https://duckduckgo.com',
        'y': 'https://search.yahoo.com/search',
    }

    async def __call__(self, req, resp, engine):
        url = self.engines[engine]
        params = {'q': req.get_param('q', True)}

        async with httpx.AsyncClient() as client:
            result = await client.get(url, params=params)

        resp.status = result.status_code
        resp.content_type = result.headers['content-type']
        resp.text = result.text


class AuthMiddleware:
    async def process_request(self, req, resp):
        token = req.get_header('Authorization')
        account_id = req.get_header('Account-ID')

        challenges = ['Token type="Fernet"']

        if token is None:
            description = 'Please provide an auth token as part of the request.'

            raise falcon.HTTPUnauthorized(
                title='Auth token required',
                description=description,
                challenges=challenges,
                href='http://docs.example.com/auth',
            )

        if not self._token_is_valid(token, account_id):
            description = (
                'The provided auth token is not valid. '
                'Please request a new token and try again.'
            )

            raise falcon.HTTPUnauthorized(
                title='Authentication required',
                description=description,
                challenges=challenges,
                href='http://docs.example.com/auth',
            )

    def _token_is_valid(self, token, account_id):
        return True  # Suuuuuure it's valid...


class RequireJSON:
    async def process_request(self, req, resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                description='This API only supports responses encoded as JSON.',
                href='http://docs.examples.com/api/json',
            )

        if req.method in ('POST', 'PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType(
                    title='This API only supports requests encoded as JSON.',
                    href='http://docs.examples.com/api/json',
                )


class TimingMiddleware:
    """Async middleware that records request processing time.

    Demonstrates using req.context and resp.context to pass
    information between middleware components and resources.
    """

    async def process_request(self, req, resp):
        req.context.request_start = time.perf_counter()

    async def process_response(self, req, resp, resource, req_succeeded):
        start = getattr(req.context, 'request_start', None)
        if start is not None:
            elapsed_ms = (time.perf_counter() - start) * 1000
            resp.set_header('Server-Timing', f'total;dur={elapsed_ms:.2f}')


def max_body(limit):
    async def hook(req, resp, resource, params):
        length = req.content_length
        if length is not None and length > limit:
            msg = (
                'The size of the request is too large. The body must not '
                'exceed ' + str(limit) + ' bytes in length.'
            )

            raise falcon.HTTPContentTooLarge(
                title='Request body is too large', description=msg
            )

    return hook


class ThingsResource:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('thingsapp.' + __name__)

    async def on_get(self, req, resp, user_id):
        marker = req.get_param('marker') or ''
        limit = req.get_param_as_int('limit') or 50

        try:
            result = await self.db.get_things(marker, limit)
        except Exception as ex:
            self.logger.error(ex)

            description = (
                'Aliens have attacked our base! We will '
                'be back as soon as we fight them off. '
                'We appreciate your patience.'
            )

            raise falcon.HTTPServiceUnavailable(
                title='Service Outage', description=description, retry_after=30
            )

        resp.media = result

        resp.set_header('Powered-By', 'Falcon')
        resp.status = falcon.HTTP_200

    @falcon.before(max_body(64 * 1024))
    async def on_post(self, req, resp, user_id):
        try:
            doc = await req.get_media()
        except falcon.errors.HTTPBadRequest:
            raise falcon.HTTPBadRequest(
                title='Missing thing',
                description='A thing must be submitted in the request body.',
            )

        proper_thing = await self.db.add_thing(doc)

        resp.status = falcon.HTTP_201
        resp.location = '/{}/things/{}'.format(user_id, proper_thing['id'])


# The app instance is an ASGI callable
app = falcon.asgi.App(
    middleware=[
        AuthMiddleware(),
        RequireJSON(),
        TimingMiddleware(),
    ]
)

db = StorageEngine()
things = ThingsResource(db)
app.add_route('/{user_id}/things', things)

# If a responder ever raises an instance of StorageError, pass control to
# the given handler.
app.add_error_handler(StorageError, StorageError.handle)

# Proxy some things to another service; this example shows how you might
# send parts of an API off to a legacy system that hasn't been upgraded
# yet, or perhaps is a single cluster that all data centers have to share.
sink = SinkAdapter()
app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')
