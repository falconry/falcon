from falcon import request_helpers, stream


def test_bounded_stream():
    assert request_helpers.Body is stream.Body
    assert request_helpers.BoundedStream is stream.BoundedStream
