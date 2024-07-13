import msgpack


class RedisCache:
    PREFIX = 'asgilook:'
    INVALIDATE_ON = frozenset({'DELETE', 'POST', 'PUT'})
    CACHE_HEADER = 'X-ASGILook-Cache'
    TTL = 3600

    def __init__(self, config):
        self._config = config
        self._redis = self._config.redis_from_url(self._config.redis_host)

    async def _serialize_response(self, resp):
        data = await resp.render_body()
        return msgpack.packb([resp.content_type, data], use_bin_type=True)

    def _deserialize_response(self, resp, data):
        resp.content_type, resp.data = msgpack.unpackb(data, raw=False)
        resp.complete = True
        resp.context.cached = True

    async def process_startup(self, scope, event):
        await self._redis.ping()

    async def process_shutdown(self, scope, event):
        await self._redis.aclose()

    async def process_request(self, req, resp):
        resp.context.cached = False

        if req.method in self.INVALIDATE_ON:
            return

        key = f'{self.PREFIX}/{req.path}'
        data = await self._redis.get(key)
        if data is not None:
            self._deserialize_response(resp, data)
            resp.set_header(self.CACHE_HEADER, 'Hit')
        else:
            resp.set_header(self.CACHE_HEADER, 'Miss')

    async def process_response(self, req, resp, resource, req_succeeded):
        if not req_succeeded:
            return

        key = f'{self.PREFIX}/{req.path}'

        if req.method in self.INVALIDATE_ON:
            await self._redis.delete(key)
        elif not resp.context.cached:
            data = await self._serialize_response(resp)
            await self._redis.set(key, data, ex=self.TTL)
