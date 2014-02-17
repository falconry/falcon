import json
import logging
from wsgiref import simple_server

import falcon


class StorageEngine:
    pass


class StorageError(Exception):
    @staticmethod
    def handle(ex, req, resp, params):
        description = ('Sorry, couldn\'t write your thing to the '
                       'database. It worked on my box.')

        raise falcon.HTTPError(falcon.HTTP_725,
                               'Database Error',
                               description)


class Proxy(object):
    def forward(self, req):
        return falcon.HTTP_503


class SinkAdapter(object):

    def __init__(self):
        self._proxy = Proxy()

    def __call__(self, req, resp, **kwargs):
        resp.status = self._proxy.forward(req)
        self.kwargs = kwargs


def token_is_valid(token, user_id):
    return True  # Suuuuuure it's valid...


def auth(req, resp, params):
    # Alternatively, use Talons or do this in WSGI middleware...
    token = req.get_header('X-Auth-Token')

    if token is None:
        description = ('Please provide an auth token '
                       'as part of the request.')

        raise falcon.HTTPUnauthorized('Auth token required',
                                      description,
                                      href='http://docs.example.com/auth')

    if not token_is_valid(token, params['user_id']):
        description = ('The provided auth token is not valid. '
                       'Please request a new token and try again.')

        raise falcon.HTTPUnauthorized('Authentication required',
                                      description,
                                      href='http://docs.example.com/auth',
                                      scheme='Token; UUID')


def check_media_type(req, resp, params):
    if not req.client_accepts_json:
        raise falcon.HTTPUnsupportedMediaType(
            'This API only supports the JSON media type.',
            href='http://docs.examples.com/api/json')


class ThingsResource:

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('thingsapp.' + __name__)

    def on_get(self, req, resp, user_id):
        marker = req.get_param('marker') or ''
        limit = req.get_param_as_int('limit') or 50

        try:
            result = self.db.get_things(marker, limit)
        except Exception as ex:
            self.logger.error(ex)

            description = ('Aliens have attacked our base! We will '
                           'be back as soon as we fight them off. '
                           'We appreciate your patience.')

            raise falcon.HTTPServiceUnavailable(
                'Service Outage',
                description,
                30)

        resp.set_header('X-Powered-By', 'Donuts')
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)

    def on_post(self, req, resp, user_id):
        try:
            # req.stream corresponds to the WSGI wsgi.input environ variable,
            # and allows you to read bytes from the request body.
            #
            # json.load assumes the input stream is encoded at utf-8 if the
            # encoding is not specified explicitly.
            #
            # See also: PEP 3333
            thing = json.load(req.stream, 'utf-8')

        except ValueError:
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect.')

        proper_thing = self.db.add_thing(thing)

        resp.status = falcon.HTTP_201
        resp.location = '/%s/things/%s' % (user_id, proper_thing.id)

# Configure your WSGI server to load "things.app" (app is a WSGI callable)
app = falcon.API(before=[auth, check_media_type])

db = StorageEngine()
things = ThingsResource(db)
app.add_route('/{user_id}/things', things)

# If a responder ever raised an instance of StorageError, pass control to
# the given handler.
app.add_error_handler(StorageError, StorageError.handle)

# Proxy some things to another service. This example shows how you might
# send parts of an API off to a legacy system that hasn't been upgraded
# yet, or perhaps is a single cluster that all datacenters have to share.
sink = SinkAdapter()
app.add_sink(sink, r'/v1/[charts|inventory]')

# Useful for debugging problems in your API; works with pdb.set_trace()
if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()
