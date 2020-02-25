from falcon.routing import CompiledRouter


class MyRouter(CompiledRouter):
    pass


class MyResponder:
    def on_get(self, req, res):
        pass

    def on_post(self, req, res):
        pass

    def on_delete(self, req, res):
        pass

    def on_get_id(self, req, res, id):
        pass

    def on_put_id(self, req, res, id):
        pass

    def on_delete_id(self, req, res, id):
        pass


class MyResponderAsync:
    async def on_get(self, req, res):
        pass

    async def on_post(self, req, res):
        pass

    async def on_delete(self, req, res):
        pass

    async def on_get_id(self, req, res, id):
        pass

    async def on_put_id(self, req, res, id):
        pass

    async def on_delete_id(self, req, res, id):
        pass


class OtherResponder:
    def on_post_id(self, *args):
        pass


class OtherResponderAsync:
    async def on_post_id(self, *args):
        pass


def sinkFn(*args):
    pass


class SinkClass:
    def __call__(self, *args):
        pass


def my_error_handler(req, resp, ex, params):
    pass


async def my_error_handler_async(req, resp, ex, params):
    pass


class MyMiddleware:
    def process_request(self, *args):
        pass

    def process_resource(self, *args):
        pass

    def process_response(self, *args):
        pass


class OtherMiddleware:
    def process_request(self, *args):
        pass

    def process_response(self, *args):
        pass


class MyMiddlewareAsync:
    async def process_request(self, *args):
        pass

    async def process_resource(self, *args):
        pass

    async def process_response(self, *args):
        pass


class OtherMiddlewareAsync:
    async def process_request(self, *args):
        pass

    async def process_response(self, *args):
        pass
