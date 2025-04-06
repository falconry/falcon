import msgspec

from falcon import Request
from falcon import Response


class MsgspecMiddleware:
    def process_resource(
        self, req: Request, resp: Response, resource: object, params: dict
    ) -> None:
        if schema := getattr(resource, f'{req.method}_SCHEMA', None):
            param = schema.__name__.lower()
            params[param] = msgspec.convert(req.get_media(), schema)
