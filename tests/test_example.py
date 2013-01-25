import json
import logging

import falcon


class StorageEngine:
    pass


class ThingsResource:

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('thingsapi.' + __name__)

    def on_get(self, req, resp):
        user_id = req.get_param('user_id', required=True)
        marker = req.get_param('marker', default='')
        limit = req.get_param('limit', default=50)

        # Alternatively, do this in middleware
        token = req.get_header('X-Auth-Token')

        if token is None:
            raise falcon.HTTPUnauthorized('Auth token required',
                                          'Please provide an auth token as '
                                          'part of the request',
                                          'http://docs.example.com/auth')

        # Note: token_is_valid is used as an example
        # and does not actually exist
        if not token_is_valid(token, user_id):
            raise falcon.HTTPUnauthorized('Authentication required',
                                          'The provided auth token is not '
                                          'valid. Please request a new token '
                                          'and try again.',
                                          'http://docs.example.com/auth')

        # Alternatively, do this in middleware
        if not req.client_accepts_json():
            raise falcon.HTTPUnsupportedMediaType(
                'Media Type not Supported',
                'This API only supports the JSON media type.',
                'http://docs.example.com/json')

        try:
            result = self.db.get_things(marker, limit)
        except Exception as ex:
            self.logger.error(ex)

            description = ('Aliens have attacked our base. We will be back '
                           'as soon as we fight them off. We appreciate your '
                           'patience.')

            raise falcon.HTTPServiceUnavailable('Service Outage', description)

        resp.set_header('X-Powered-By', 'Donuts')
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)

    def on_post(self, req, resp):
        try:
            raw_json = req.body.read()
        except Exception:
            raise falcon.HTTPError(falcon.HTTP_748,
                                   'Read Error',
                                   "Could not read the request body. I bet "
                                   "it's them ponies again.")

        try:
            thing = json.loads(raw_json, 'utf-8')
        except ValueError:
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect.')

        try:
            proper_thing = self.db.add_thing(thing)
        # Note: StorageError is used as an example
        # and does not actually exist
        except StorageError:
            raise falcon.HTTPError(falcon.HTTP_725,
                                   'Database Error',
                                   "Sorry, couldn't write your thing to the "
                                   'database. It worked on my machine.')

        resp.status = falcon.HTTP_201
        resp.set_header('Location', '/{userId}/things/' + proper_thing.id)

wsgi_app = api = falcon.API()

db = StorageEngine()
things = ThingsResource(db)
api.add_route('/{user_id}/things', things)
