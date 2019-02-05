from functools import partial
import io
import json
import platform
import sys

import mujson
import pytest
import ujson

from falcon import media

orjson = None
rapidjson = None
if sys.version_info >= (3, 5):
    import rapidjson

    if platform.python_implementation() == 'CPython':
        import orjson


COMMON_SERIALIZATION_PARAM_LIST = [
    # Default json.dumps, with only ascii
    (None, {'test': 'value'}, b'{"test":"value"}'),
    (mujson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    (ujson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    (partial(lambda media, **kwargs: json.dumps([media, kwargs]),
     ensure_ascii=True),
     {'test': 'value'},
     b'[{"test":"value"},{"ensure_ascii":true}]'),
]

COMMON_DESERIALIZATION_PARAM_LIST = [
    (None, b'[1, 2]', [1, 2]),
    (partial(json.loads,
             object_hook=lambda data: {k: v.upper() for k, v in data.items()}),
     b'{"key": "value"}',
     {'key': 'VALUE'}),

    (mujson.loads, b'{"test": "value"}', {'test': 'value'}),
    (ujson.loads, b'{"test": "value"}', {'test': 'value'}),
]

YEN = b'\xc2\xa5'

if orjson:
    SERIALIZATION_PARAM_LIST = COMMON_SERIALIZATION_PARAM_LIST + [
        # Default json.dumps, with non-ascii characters
        (None, {'yen': YEN.decode()}, b'{"yen":"' + YEN + b'"}'),

        # Extra Python 3 json libraries
        (rapidjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
        (orjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]

    DESERIALIZATION_PARAM_LIST = COMMON_DESERIALIZATION_PARAM_LIST + [
        (rapidjson.loads, b'{"test": "value"}', {'test': 'value'}),
        (orjson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
elif rapidjson:
    SERIALIZATION_PARAM_LIST = COMMON_SERIALIZATION_PARAM_LIST + [
        # Default json.dumps, with non-ascii characters
        (None, {'yen': YEN.decode()}, b'{"yen":"' + YEN + b'"}'),

        # Extra Python 3 json libraries
        (rapidjson.dumps, {'test': 'value'}, b'{"test":"value"}'),
    ]

    DESERIALIZATION_PARAM_LIST = COMMON_DESERIALIZATION_PARAM_LIST + [
        (rapidjson.loads, b'{"test": "value"}', {'test': 'value'}),
    ]
else:
    SERIALIZATION_PARAM_LIST = COMMON_SERIALIZATION_PARAM_LIST + [
        # Default json.dumps, with non-ascii characters
        (None, {'yen': YEN.decode('utf-8')}, b'{"yen":"' + YEN + b'"}'),
    ]
    DESERIALIZATION_PARAM_LIST = COMMON_DESERIALIZATION_PARAM_LIST


@pytest.mark.parametrize('func, body, expected', SERIALIZATION_PARAM_LIST)
def test_serialization(func, body, expected):
    JH = media.JSONHandler(dumps=func)

    # NOTE(nZac) PyPy and CPython render the final string differently. One
    # includes spaces and the other doesn't. This replace will normalize that.
    assert JH.serialize(body, b'application/javacript').replace(b' ', b'') == expected  # noqa


@pytest.mark.parametrize('func, body, expected', DESERIALIZATION_PARAM_LIST)
def test_deserialization(func, body, expected):
    JH = media.JSONHandler(loads=func)

    assert JH.deserialize(
        io.BytesIO(body),
        'application/javacript',
        len(body)
    ) == expected
