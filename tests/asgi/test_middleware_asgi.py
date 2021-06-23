import pytest

import falcon


class MiddlewareIncompatibleWithWSGI_A:
    async def process_request(self, req, resp):
        pass


class MiddlewareIncompatibleWithWSGI_B:
    async def process_resource(self, req, resp, resource, params):
        pass


class MiddlewareIncompatibleWithWSGI_C:
    async def process_response(self, req, resp, resource, req_succeeded):
        pass


@pytest.mark.parametrize(
    'middleware',
    [
        MiddlewareIncompatibleWithWSGI_A(),
        MiddlewareIncompatibleWithWSGI_B(),
        MiddlewareIncompatibleWithWSGI_C(),
        (MiddlewareIncompatibleWithWSGI_C(), MiddlewareIncompatibleWithWSGI_A()),
    ],
)
def test_raise_on_incompatible(middleware):
    api = falcon.App()

    with pytest.raises(falcon.CompatibilityError):
        api.add_middleware(middleware)
