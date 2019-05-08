import pytest

from falcon import PY35


def test_asgi():
    if PY35:
        with pytest.raises(ImportError):
            import falcon.asgi
    else:
        # Should not raise
        import falcon.asgi  # NOQA
