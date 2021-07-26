from falcon.vendor import mimeparse


# TODO(vytas): Remove this test since it makes little sense now that
#   we have vendored python-mimeparse?


def test_deps_mimeparse_correct_package():
    """Ensure we are dealing with python-mimeparse, not mimeparse."""

    tokens = mimeparse.mimeparse.__version__.split('.')

    # NOTE(kgriffs): python-mimeparse starts at version 1.5.2,
    # whereas the mimeparse package is at version 0.1.4 at the time
    # of this writing.
    assert int(tokens[0]) > 0, 'Incorrect vendored dependency version detected'
