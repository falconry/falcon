from datetime import datetime
import string

import pytest

from falcon.routing import converters


@pytest.mark.parametrize('fragment, num_digits, min, max, expected', [
    ('123', None, None, None, 123),
    ('01', None, None, None, 1),
    ('001', None, None, None, 1),
    ('0', None, None, None, 0),
    ('00', None, None, None, 00),

    ('1', 1, None, None, 1),
    ('12', 1, None, None, None),
    ('12', 2, None, None, 12),

    ('1', 1, 1, 1, 1),
    ('1', 1, 1, None, 1),
    ('1', 1, 1, 2, 1),
    ('1', 1, 2, None, None),
    ('1', 1, 2, 1, None),
    ('2', 1, 1, 2, 2),
    ('2', 1, 2, 2, 2),
    ('3', 1, 1, 2, None),

    ('12', 1, None, None, None),
    ('12', 1, 1, 12, None),
    ('12', 2, None, None, 12),
    ('12', 2, 1, 12, 12),
    ('12', 2, 12, 12, 12),
    ('12', 2, 13, 12, None),
    ('12', 2, 13, 13, None),
])
def test_int_converter(fragment, num_digits, min, max, expected):
    c = converters.IntConverter(num_digits, min, max)
    assert c.convert(fragment) == expected


@pytest.mark.parametrize('fragment', (
    ['0x0F', 'something', '', ' '] +
    ['123' + w for w in string.whitespace] +
    [w + '123' for w in string.whitespace]
))
def test_int_converter_malformed(fragment):
    c = converters.IntConverter()
    assert c.convert(fragment) is None


@pytest.mark.parametrize('num_digits', [0, -1, -10])
def test_int_converter_invalid_config(num_digits):
    with pytest.raises(ValueError):
        converters.IntConverter(num_digits)


@pytest.mark.parametrize('fragment, format_string, expected', [
    ('07-03-17', '%m-%d-%y', datetime(2017, 7, 3)),
    ('07-03-17 ', '%m-%d-%y ', datetime(2017, 7, 3)),
    ('2017-07-03T14:30:01Z', '%Y-%m-%dT%H:%M:%SZ', datetime(2017, 7, 3, 14, 30, 1)),
    ('2017-07-03T14:30:01', '%Y-%m-%dT%H:%M:%S', datetime(2017, 7, 3, 14, 30, 1)),
    ('2017-07-03T14:30:01', '%Y-%m-%dT%H:%M:%SZ', None),
    ('2017_19', '%Y_%H', datetime(2017, 1, 1, 19, 0)),
    ('07-03-17 ', '%m-%d-%y', None),
    (' 07-03-17', '%m-%d-%y', None),
    ('07 -03-17', '%m-%d-%y', None),
])
def test_datetime_converter(fragment, format_string, expected):
    c = converters.DateTimeConverter(format_string)
    assert c.convert(fragment) == expected


def test_datetime_converter_default_format():
    c = converters.DateTimeConverter()
    assert c.convert('2017-07-03T14:30:01Z') == datetime(2017, 7, 3, 14, 30, 1)
