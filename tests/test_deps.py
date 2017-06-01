import mimeparse


def test_deps_mimeparse_correct_package():
    """Ensure we are dealing with python-mimeparse, not mimeparse."""

    tokens = mimeparse.__version__.split('.')
    msg = (
        'Incorrect dependency detected. Please install the '
        '"python-mimeparse" package instead of the "mimeparse" '
        'package.'
    )

    # NOTE(kgriffs): python-mimeparse starts at version 1.5.2,
    # whereas the mimeparse package is at version 0.1.4 at the time
    # of this writing.
    assert int(tokens[0]) > 0, msg
