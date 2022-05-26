import pytest

from falcon import app_helpers, request_helpers, stream

from _util import has_cython  # NOQA


def test_bounded_stream():
    assert request_helpers.Body is stream.Body
    assert request_helpers.BoundedStream is stream.BoundedStream
