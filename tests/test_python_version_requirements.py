import pytest

from falcon import ASGI_SUPPORTED

# from _util import CYTHON  # NOQA


def test_asgi():
    if ASGI_SUPPORTED:
        # Should not raise
        import falcon.asgi  # NOQA
    else:
        with pytest.raises(ImportError):
            import falcon.asgi  # NOQA
