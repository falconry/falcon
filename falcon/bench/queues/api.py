# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import falcon
from falcon.bench.queues import claims
from falcon.bench.queues import messages
from falcon.bench.queues import queues
from falcon.bench.queues import stats


class RequestIDComponent(object):
    def process_request(self, req, resp):
        req.context.request_id = '<generate ID>'

    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('X-Request-ID', req.context.request_id)


class CannedResponseComponent(object):
    def __init__(self, body, headers):
        self._body = body
        self._headers = headers

    def process_response(self, req, resp, resource, req_succeeded):
        user_agent = req.user_agent  # NOQA
        limit = req.get_param('limit') or '10'  # NOQA

        resp.status = falcon.HTTP_200
        resp.data = self._body
        resp.set_headers(self._headers)
        resp.vary = ('X-Auth-Token', 'Accept-Encoding')
        resp.content_range = (0, len(self._body), len(self._body) + 100)


def create(body, headers):
    queue_collection = queues.CollectionResource()
    queue_item = queues.ItemResource()

    stats_endpoint = stats.Resource()

    msg_collection = messages.CollectionResource()
    msg_item = messages.ItemResource()

    claim_collection = claims.CollectionResource()
    claim_item = claims.ItemResource()

    middleware = [
        RequestIDComponent(),
        CannedResponseComponent(body, headers),
    ]

    api = falcon.API(middleware=middleware)
    api.add_route('/v1/{tenant_id}/queues', queue_collection)
    api.add_route('/v1/{tenant_id}/queues/{queue_name}', queue_item)
    api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                  '/stats', stats_endpoint)
    api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                  '/messages', msg_collection)
    api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                  '/messages/{message_id}', msg_item)
    api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                  '/claims', claim_collection)
    api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                  '/claims/{claim_id}', claim_item)

    return api
