import platform

import pytest


import falcon


# NOTE(kgriffs): Some modules actually run a wsgiref server, so
# to ensure we reset the detection for the other modules, we just
# run this fixture before each one is tested.
@pytest.fixture(autouse=True, scope='module')
def reset_request_stream_detection():
    falcon.Request._wsgi_input_type_known = False
    falcon.Request._always_wrap_wsgi_input = False


# NOTE(kgriffs): Patch pytest to make it compatible with Jython. This
# is necessary because val.encode() raises UnicodeEncodeError instead
# of UnicodeDecodeError, and running under Jython triggers this buggy
# code path in pytest.
if platform.python_implementation() == 'Jython':
    import _pytest.python

    def _escape_strings(val):
        if isinstance(val, bytes):
            try:
                return val.encode('ascii')
            except UnicodeEncodeError:
                return val.encode('string-escape')
        else:
            return val.encode('unicode-escape')

    _pytest.python._escape_strings = _escape_strings
