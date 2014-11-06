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
    def process_request(self, req, resp, params):
        req.context['request_id'] = '<generate ID>'

    def process_response(self, req, resp):
        resp.set_header('X-Request-ID', req.context['request_id'])


class NoopComponent(object):
    def process_request(self, req, resp, params):
        pass


def create(body, headers):
    vary = ('X-Auth-Token', 'Accept-Encoding')

    def canned_response(req, resp):
        resp.status = falcon.HTTP_200
        resp.body = body
        resp.set_headers(headers)
        resp.vary = vary
        resp.content_range = (0, len(body), len(body) + 100)

    queue_collection = queues.CollectionResource()
    queue_item = queues.ItemResource()

    stats_endpoint = stats.Resource()

    msg_collection = messages.CollectionResource()
    msg_item = messages.ItemResource()

    claim_collection = claims.CollectionResource()
    claim_item = claims.ItemResource()

    middleware = [NoopComponent(), RequestIDComponent()]
    api = falcon.API(after=canned_response, middleware=middleware)
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
