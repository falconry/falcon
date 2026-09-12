import falcon


def test_asgi():
    # TODO(vytas): consider removing this file completely.
    #   Its only purpose left is verifying that ASGI_SUPPORTED is still
    #   available for compatibility.
    assert falcon.ASGI_SUPPORTED
