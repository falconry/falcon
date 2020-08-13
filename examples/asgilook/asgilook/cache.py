import msgpack


class RedisCache:
    PREFIX = 'asgilook:'
    INVALIDATE_ON = frozenset({'DELETE', 'POST', 'PUT'})
    CACHE_HEADER = 'X-ASGILook-Cache'
    TTL = 3600

    def __init__(self, config):
        self.config = config

        # NOTE(vytas): To be initialized upon application startup (see the
        #   method below).
        self.redis = None

    async def process_startup(self, scope, event):
        if self.redis is None:
            self.redis = await self.config.create_redis_pool(
                self.config.redis_host)

    async def serialize_response(self, resp):
        data = await resp.render_body()
        return msgpack.packb([resp.content_type, data], use_bin_type=True)

    def deserialize_response(self, resp, data):
        resp.content_type, resp.data = msgpack.unpackb(data, raw=False)
        resp.complete = True
        resp.context.cached = True

    async def process_request(self, req, resp):
        resp.context.cached = False

        if req.method in self.INVALIDATE_ON:
            return

        key = f'{self.PREFIX}/{req.path}'
        data = await self.redis.get(key)
        if data is not None:
            self.deserialize_response(resp, data)
            resp.set_header(self.CACHE_HEADER, 'Hit')
        else:
            resp.set_header(self.CACHE_HEADER, 'Miss')

    async def process_response(self, req, resp, resource, req_succeeded):
        if not req_succeeded:
            return

        key = f'{self.PREFIX}/{req.path}'

        if req.method in self.INVALIDATE_ON:
            await self.redis.delete(key)
        elif not resp.context.cached:
            data = await self.serialize_response(resp)
            await self.redis.set(key, data, expire=self.TTL)
