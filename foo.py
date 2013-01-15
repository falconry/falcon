import json
import logging

import falcon

class StorageEngine:
    pass


class ThingsResource:

    def __init__(self):
      pass

    def on_get(self, req, resp):
        raise IOError()

app = api = falcon.API()

things = ThingsResource()
api.add_route('/{user_id}/things', things)
