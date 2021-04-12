import pytest

from falcon import app_helpers, request_helpers, stream

# from _util import has_cython


def test_bounded_stream():
    assert request_helpers.Body is stream.Body
    assert request_helpers.BoundedStream is stream.BoundedStream


class TestApiHelpers:
    @pytest.mark.filterwarnings('ignore:The api_helpers')
    def test_imports(self):
        from falcon import api_helpers

        for name in app_helpers.__all__:
            assert getattr(api_helpers, name) is getattr(app_helpers, name)

    # TODO enable test of deprecation
    # @pytest.mark.skipif(has_cython, reason='Reloading modules on Cython does not work')
    # def test_warning(self):
    #     import importlib

    #     from falcon.util.deprecation import DeprecatedWarning

    #     with pytest.warns(DeprecatedWarning, match='The api_helpers'):
    #         from falcon import api_helpers
    #         importlib.reload(api_helpers)
